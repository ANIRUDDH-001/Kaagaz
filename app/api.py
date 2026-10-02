"""REST API. Every route except health and household creation needs the household token."""
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.actions import ActionError, bind_to_card, execute_actions, mark_done, snooze
from app.clock import now_utc, today_ist
from app.db import ROLES
from app.inputs import ERRORS
from flows.process_workflow import ProcessInputWorkflow
from flows.schedule import next_point
from flows.temporal import PROCESS_TIMEOUT

router = APIRouter(prefix="/api")
MAX_UPLOAD = 8 * 1024 * 1024
MAX_TEXT = 500
LIMIT_MESSAGE = "इस घंटे की AI सीमा पूरी हो गई — थोड़ी देर बाद कोशिश करें।"
TTS_LIMIT_MESSAGE = "इस घंटे की आवाज़ सीमा पूरी हो गई — फ़ोन की अपनी आवाज़ में सुनाऊँगा।"


class RoleBody(BaseModel):
    role: str = "parent"


class SnoozeBody(BaseModel):
    until: str
    role: str = "parent"


class ConfirmBody(BaseModel):
    actions: list[dict[str, Any]]
    role: str = "parent"


class PushBody(BaseModel):
    role: str
    subscription: dict[str, Any]


class TTSBody(BaseModel):
    text: str


def _role(role: str) -> str:
    if role not in ROLES:
        raise HTTPException(422, "role must be parent or son")
    return role


async def household(request: Request, authorization: str = Header(default="")) -> dict:
    token = authorization.removeprefix("Bearer ").strip()
    hh = await request.app.state.store.household_by_token(token) if token else None
    if hh is None:
        raise HTTPException(401, "unknown household")
    return hh


async def _obligation(request: Request, oid: str, hh: dict) -> dict:
    ob = await request.app.state.store.get_obligation(oid, hh["_id"])
    if ob is None:
        raise HTTPException(404, "वह काग़ज़ नहीं मिला।")
    return ob


def _public_obligation(o: dict, mode: str, now) -> dict:
    p = next_point(o, mode, now)
    return {"id": o["_id"], "title": o.get("title"), "title_hi": o.get("title_hi"), "category": o.get("category"),
            "amount_inr": o.get("amount_inr"), "due_date": o["due_date"], "action": o.get("action"),
            "consequence": o.get("consequence"), "status": o["status"], "snoozed_until": o.get("snoozed_until"),
            "next": {"label": p.label, "kind": p.kind, "at": p.at.isoformat()} if p else None}


def _public_notification(n: dict) -> dict:
    return {"id": n["_id"], "kind": n["kind"], "obligation_id": n.get("obligation_id"), "text_hi": n["text_hi"],
            "text_en": n.get("text_en"), "created_at": n["created_at"].isoformat(), "read": n.get("read_at") is not None}


def client_ip(request: Request) -> str:
    # First X-Forwarded-For hop (Render's proxy sets it). A client can forge it, but that only buys what having
    # no per-address limit gave; the global caps still hold. The last hop could lump every visitor together.
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


@router.post("/households")
async def create_household(request: Request):
    if not request.app.state.household_ip_limiter.allow(client_ip(request)):
        raise HTTPException(429, "बहुत सारे नए खाते बन गए — थोड़ी देर बाद आइए।")
    token, hh = await request.app.state.store.create_household(request.app.state.settings.app_mode, now_utc())
    return {"token": token, "household_id": hh["_id"], "mode": hh["mode"],
            "expires_at": hh["expires_at"].isoformat() if hh["expires_at"] else None}


@router.get("/state")
async def state(request: Request, role: str = "parent", hh: dict = Depends(household)):
    _role(role)
    store = request.app.state.store
    now = now_utc()
    obligations = await store.list_obligations(hh["_id"])
    notes = await store.list_notifications(hh["_id"], role)
    return {"mode": hh["mode"], "role": role, "today": today_ist(now).isoformat(),
            "obligations": [_public_obligation(o, hh["mode"], now) for o in obligations],
            "inbox": [_public_notification(n) for n in notes],
            "unread": sum(1 for n in notes if not n.get("read_at"))}


@router.post("/inputs")
async def create_input(request: Request, kind: str = Form(...), role: str = Form("parent"),
                       text: str | None = Form(None), file: UploadFile | None = File(None),
                       hh: dict = Depends(household)):
    _role(role)
    if kind not in ("photo", "voice", "text"):
        raise HTTPException(422, "kind must be photo, voice or text")
    data = mime = None
    if kind in ("photo", "voice"):
        if file is None:
            raise HTTPException(422, "file required")
        data = await file.read(MAX_UPLOAD + 1)
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "फ़ाइल बहुत बड़ी है (8 MB से ज़्यादा) — छोटी फ़ोटो भेजिए।")
        if not data:
            raise HTTPException(422, "empty file")
        mime = file.content_type or ("image/jpeg" if kind == "photo" else "audio/webm")
    else:
        text = (text or "").strip()
        if not text or len(text) > MAX_TEXT:
            raise HTTPException(422, "text must be 1-500 characters")
    s = request.app.state
    # Households are free to create, so the per-household limit alone can be dodged: per-address and global caps too.
    if hh["mode"] == "demo" and not (s.limiter.allow(hh["_id"]) and s.ip_limiter.allow(client_ip(request))
                                     and s.global_limiter.allow("all")):
        raise HTTPException(429, LIMIT_MESSAGE)
    p = s.inputs.create(hh["_id"], role, kind, data, mime, text)
    await s.temporal.start_workflow(ProcessInputWorkflow.run, p.id, id=f"input-{p.id}", task_queue=s.ai_queue,
                                    execution_timeout=PROCESS_TIMEOUT)
    return {"input_id": p.id}


def _pending(request: Request, input_id: str, hh: dict):
    p = request.app.state.inputs.get(input_id)
    if p is None or p.household_id != hh["_id"]:
        raise HTTPException(404, ERRORS["Gone"])
    return p


@router.get("/inputs/{input_id}")
async def get_input(input_id: str, request: Request, hh: dict = Depends(household)):
    p = _pending(request, input_id, hh)
    return {"status": p.status, "kind": p.kind, "transcript": p.transcript, "card": p.card, "error": p.error,
            "message": ERRORS.get(p.error) if p.error else None}


@router.post("/inputs/{input_id}/confirm")
async def confirm_input(input_id: str, body: ConfirmBody, request: Request, hh: dict = Depends(household)):
    _role(body.role)
    p = _pending(request, input_id, hh)
    if p.status == "confirmed":
        return {"results": p.results}   # a retry (lost response, double tap): same answer, nothing twice
    if p.status != "ready":
        raise HTTPException(409, "पहले से सेव हो रहा है।" if p.status == "confirming" else "not ready yet")
    try:
        actions = bind_to_card(p.card["actions"], body.actions)
    except ActionError as e:
        raise HTTPException(422, str(e)) from None
    p.status = "confirming"   # set before the first await, so a concurrent confirm gets 409
    try:
        results = await execute_actions(request.app.state.store, request.app.state.temporal, hh, actions,
                                        body.role, now_utc(), input_id=p.id)
    except ActionError as e:
        p.status = "ready"
        raise HTTPException(422, str(e)) from None
    except Exception:
        p.status = "ready"    # safe to retry: obligation ids come from the input id
        raise
    p.status, p.results = "confirmed", results
    return {"results": results}


@router.post("/obligations/{oid}/done")
async def done(oid: str, body: RoleBody, request: Request, hh: dict = Depends(household)):
    ob = await _obligation(request, oid, hh)
    await mark_done(request.app.state.store, request.app.state.temporal, ob, _role(body.role), now_utc())
    return {"ok": True}


@router.post("/obligations/{oid}/snooze")
async def snooze_route(oid: str, body: SnoozeBody, request: Request, hh: dict = Depends(household)):
    ob = await _obligation(request, oid, hh)
    try:
        await snooze(request.app.state.store, request.app.state.temporal, ob, body.until, _role(body.role), now_utc())
    except ActionError as e:
        raise HTTPException(422, str(e)) from None
    return {"ok": True}


@router.post("/notifications/{nid}/read")
async def read_notification(nid: str, request: Request, hh: dict = Depends(household)):
    if not await request.app.state.store.mark_read(hh["_id"], nid, now_utc()):
        raise HTTPException(404, "not found")
    return {"ok": True}


@router.post("/push/subscribe")
async def subscribe(body: PushBody, request: Request, hh: dict = Depends(household)):
    sub = body.subscription
    keys = sub.get("keys") or {}
    if not str(sub.get("endpoint", "")).startswith("https://") or not keys.get("p256dh") or not keys.get("auth"):
        raise HTTPException(422, "invalid push subscription")
    await request.app.state.store.add_push(hh["_id"], _role(body.role),
                                           {"endpoint": sub["endpoint"], "keys": {"p256dh": keys["p256dh"],
                                                                                 "auth": keys["auth"]}})
    return {"ok": True}


@router.post("/tts")
async def tts(body: TTSBody, request: Request, hh: dict = Depends(household)):
    engine = request.app.state.tts
    if engine is None:
        raise HTTPException(404, "server voice is off; the browser speaks")
    text = body.text.strip()
    if not text or len(text) > 400:
        raise HTTPException(422, "text must be 1-400 characters")
    s = request.app.state
    if hh["mode"] == "demo" and not (s.tts_limiter.allow(hh["_id"]) and s.tts_global_limiter.allow("all")):
        raise HTTPException(429, TTS_LIMIT_MESSAGE)   # the browser falls back to its own voice
    try:
        audio = await engine.synthesize(text)
    except Exception:  # noqa: BLE001  quota used up or ElevenLabs down: the browser voice takes over
        raise HTTPException(503, "server voice unavailable") from None
    return Response(audio, media_type="audio/mpeg")
