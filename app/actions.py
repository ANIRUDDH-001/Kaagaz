"""Run confirmed actions. The only code path that changes obligations or starts workflows."""
from datetime import date, datetime

from pymongo.errors import DuplicateKeyError
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.service import RPCError

from ai.understand import validate_create
from app.clock import today_ist
from flows.obligation_workflow import ObligationArgs, ObligationWorkflow
from flows.temporal import TASK_QUEUE

STORED_FIELDS = ("title", "title_hi", "category", "amount_inr", "due_date", "action", "consequence",
                 "evidence_amount", "evidence_due_date", "evidence_consequence", "summary_hi",
                 "remind_offsets_days", "escalate", "source")
CHANGES = ("create_obligation", "mark_done", "snooze", "update_obligation")
# What the confirmation card lets the user edit. Everything else comes from the card the server made.
EDITABLE = {"create_obligation": ("title", "title_hi", "amount_inr", "due_date", "action", "escalate",
                                  "remind_offsets_days")}
CARD_CHANGED = "यह कार्ड बदल गया है — कृपया फिर से भेजिए।"


class ActionError(Exception):
    """A confirmed action can't be carried out; the message is shown to the user (Hindi)."""


def bind_to_card(card_actions: list[dict], submitted: list[dict]) -> list[dict]:
    """Confirm means "yes to this card". The browser may change only the fields the card shows as
    editable; it can't add, drop, swap or retarget an action that Gemma didn't propose."""
    proposed = [a for a in card_actions if a.get("tool") in CHANGES]
    if len(submitted) != len(proposed):
        raise ActionError(CARD_CHANGED)
    bound = []
    for want, got in zip(proposed, submitted):
        if got.get("tool") != want["tool"] or got.get("obligation_id") != want.get("obligation_id"):
            raise ActionError(CARD_CHANGED)
        bound.append({**want, **{k: got[k] for k in EDITABLE.get(want["tool"], ()) if k in got}})
    return bound


async def _signal(temporal, workflow_id: str, signal, *args) -> None:
    try:
        await temporal.get_workflow_handle(workflow_id).signal(signal, *args)
    except RPCError:
        pass   # the workflow already finished (all reminders sent); the database change still stands


def _event(now: datetime, role: str, event: str, detail=None) -> dict:
    return {"at": now, "by_role": role, "event": event, "detail": detail}


async def create_obligation(store, temporal, hh: dict, a: dict, role: str, now: datetime,
                            oid: str, input_id: str) -> dict:
    """`oid` is derived from the input, so a retried confirm finds its own record instead of adding one."""
    v = validate_create(a, today_ist(now), source="confirm")
    if not v["due_date"]:
        raise ActionError("आख़िरी तारीख़ ज़रूरी है — कृपया तारीख़ भरिए।")
    doc = {"_id": oid, "household_id": hh["_id"], **{k: v[k] for k in STORED_FIELDS},
           "status": "active", "snoozed_until": None, "snoozed_at": None, "workflow_id": f"obligation-{oid}",
           "source_input_id": input_id, "history": [_event(now, role, "created")], "created_at": now,
           "expires_at": hh.get("expires_at")}
    try:
        await store.insert_obligation(doc)
    except DuplicateKeyError:
        pass   # a retry after a crash: the record exists; make sure its workflow does too
    args = ObligationArgs(oid, hh["_id"], v["due_date"], v["remind_offsets_days"],
                          "demo" if hh["mode"] == "demo" else "real", v["escalate"])
    try:
        await temporal.start_workflow(ObligationWorkflow.run, args, id=doc["workflow_id"], task_queue=TASK_QUEUE,
                                      id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE)
    except WorkflowAlreadyStartedError:
        pass
    return {"tool": "create_obligation", "ok": True, "obligation_id": oid}


async def mark_done(store, temporal, ob: dict, role: str, now: datetime) -> None:
    if ob["status"] == "done":
        return
    await store.set_obligation(ob["_id"], {"status": "done", "done_at": now}, _event(now, role, "done"))
    await _signal(temporal, ob["workflow_id"], ObligationWorkflow.mark_done)


async def snooze(store, temporal, ob: dict, until: str, role: str, now: datetime) -> None:
    try:
        d = date.fromisoformat(until)
    except (TypeError, ValueError):
        raise ActionError("तारीख़ समझ नहीं आई।") from None
    if d < today_ist(now):
        raise ActionError("बीती हुई तारीख़ पर याद नहीं दिला सकते — आगे की तारीख़ चुनिए।")
    if ob["status"] != "active":
        raise ActionError("यह काम पहले ही पूरा हो चुका है।")
    await store.set_obligation(ob["_id"], {"snoozed_until": d.isoformat(), "snoozed_at": now},
                               _event(now, role, "snooze", d.isoformat()))
    await _signal(temporal, ob["workflow_id"], ObligationWorkflow.snooze, d.isoformat())


async def update_obligation(store, temporal, ob: dict, a: dict, role: str, now: datetime) -> None:
    fields = {}
    if a.get("amount_inr") is not None:
        amount = float(a["amount_inr"])
        if not 0 < amount < 1e7:
            raise ActionError("रकम सही नहीं लग रही।")
        fields["amount_inr"] = amount
    if a.get("due_date"):
        try:
            fields["due_date"] = date.fromisoformat(a["due_date"]).isoformat()
        except ValueError:
            raise ActionError("तारीख़ समझ नहीं आई।") from None
    if not fields:
        raise ActionError("कुछ बदला नहीं।")
    await store.set_obligation(ob["_id"], fields, _event(now, role, "update", fields))
    if fields.get("due_date") and fields["due_date"] != ob["due_date"]:
        await _signal(temporal, ob["workflow_id"], ObligationWorkflow.update_due, fields["due_date"])


async def execute_actions(store, temporal, hh: dict, actions: list[dict], role: str, now: datetime,
                          input_id: str) -> list[dict]:
    results = []
    for n, a in enumerate(actions):
        tool = a.get("tool")
        if tool == "create_obligation":
            results.append(await create_obligation(store, temporal, hh, a, role, now, f"{input_id}-{n}", input_id))
        elif tool in ("mark_done", "snooze", "update_obligation"):
            ob = await store.get_obligation(a.get("obligation_id") or "", hh["_id"])
            if ob is None:
                raise ActionError("वह काग़ज़ नहीं मिला।")
            if tool == "mark_done":
                await mark_done(store, temporal, ob, role, now)
            elif tool == "snooze":
                await snooze(store, temporal, ob, a.get("until") or "", role, now)
            else:
                await update_obligation(store, temporal, ob, a, role, now)
            results.append({"tool": tool, "ok": True, "obligation_id": ob["_id"]})
        else:
            results.append({"tool": tool, "ok": True})
    return results
