import asyncio
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.ratelimit import HourlyLimiter
from flows.temporal import PROCESS_TIMEOUT
from tests.fakes import FakePush, FakeTemporal, FakeTTS, mock_store

DUE = (date.today() + timedelta(days=70)).isoformat()


def card(due=DUE):
    return {"kind": "paper", "transcript": None, "summary_hi": "बीमा का नोटिस।", "readback_hi": "…",
            "actions": [{"tool": "create_obligation", "source": "photo", "title": "Car insurance renewal",
                         "title_hi": "गाड़ी का इंश्योरेंस", "category": "motor_insurance", "amount_inr": 18400,
                         "due_date": due, "action": "Renew", "consequence": None, "evidence_amount": "₹ 18,400",
                         "evidence_due_date": "14/12/2026", "evidence_consequence": None, "summary_hi": "…",
                         "remind_offsets_days": [30, 7, 1], "escalate": True, "needs_check": []}]}


@pytest.fixture
def ctx(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_MODE", "demo")
    monkeypatch.setenv("TTS_BACKEND", "browser")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()
    store, temporal = mock_store(), FakeTemporal()
    app = create_app(store=store, temporal=temporal, push=FakePush(), start_workers=False)
    with TestClient(app) as c:
        h = c.post("/api/households").json()
        c.headers["Authorization"] = f"Bearer {h['token']}"
        yield SimpleNamespace(c=c, store=store, temporal=temporal, app=app, hid=h["household_id"])


def ready_input(ctx, the_card=None, hid=None):
    p = ctx.app.state.inputs.create(hid or ctx.hid, "parent", "photo", b"x", "image/jpeg")
    p.status, p.card = "ready", the_card or card()
    return p


def confirm_one(ctx):
    p = ready_input(ctx)
    r = ctx.c.post(f"/api/inputs/{p.id}/confirm", json={"actions": p.card["actions"], "role": "parent"})
    assert r.status_code == 200, r.text
    return r.json()["results"][0]["obligation_id"]


def test_requires_household_token(ctx):
    assert ctx.c.get("/api/state", headers={"Authorization": ""}).status_code == 401
    assert ctx.c.get("/api/state", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_text_input_starts_processing_on_this_process_queue(ctx):
    r = ctx.c.post("/api/inputs", data={"kind": "text", "text": "bijli ka bill kab hai", "role": "parent"})
    assert r.status_code == 200
    started = ctx.temporal.started[-1]
    assert started["workflow"] == "ProcessInputWorkflow.run" and started["arg"] == r.json()["input_id"]
    assert started["task_queue"] == ctx.app.state.ai_queue and started["task_queue"].startswith("kaagaz-ai-")
    assert started["execution_timeout"] == PROCESS_TIMEOUT   # never stranded if this process dies
    assert ctx.c.get(f"/api/inputs/{r.json()['input_id']}").json()["status"] == "processing"


def test_photo_over_8mb_is_rejected(ctx):
    big = b"0" * (8 * 1024 * 1024 + 1)
    r = ctx.c.post("/api/inputs", data={"kind": "photo"}, files={"file": ("big.jpg", big, "image/jpeg")})
    assert r.status_code == 413 and "8 MB" in r.json()["detail"]["en"] and r.json()["detail"]["code"] == "file_too_big"


def test_bad_kind_and_empty_text_are_rejected(ctx):
    assert ctx.c.post("/api/inputs", data={"kind": "video", "text": "x"}).status_code == 422
    assert ctx.c.post("/api/inputs", data={"kind": "text", "text": "   "}).status_code == 422


def test_demo_households_get_15_ai_calls_an_hour(ctx):
    codes = [ctx.c.post("/api/inputs", data={"kind": "text", "text": f"q{i}"}).status_code for i in range(16)]
    assert codes[:15] == [200] * 15 and codes[15] == 429


def test_unknown_or_foreign_input_is_404_with_send_again(ctx):
    r = ctx.c.get("/api/inputs/nope")
    assert r.status_code == 404 and "फिर से भेजिए" in r.json()["detail"]["hi"]
    other = ready_input(ctx, hid="someone-else")
    assert ctx.c.get(f"/api/inputs/{other.id}").status_code == 404


def test_confirm_creates_obligation_and_starts_reminders(ctx):
    p = ready_input(ctx)
    r = ctx.c.post(f"/api/inputs/{p.id}/confirm", json={"actions": p.card["actions"], "role": "parent"})
    assert r.status_code == 200
    started = ctx.temporal.started[-1]
    assert started["workflow"] == "ObligationWorkflow.run" and started["task_queue"] == "kaagaz"
    assert started["arg"].schedule == "demo" and started["arg"].offsets == [30, 7, 1] and started["arg"].escalate
    assert started["id"] == f"obligation-{r.json()['results'][0]['obligation_id']}"
    state = ctx.c.get("/api/state").json()
    assert state["obligations"][0]["amount_inr"] == 18400
    assert state["obligations"][0]["next"]["label"] == "d30"
    assert ctx.c.get(f"/api/inputs/{p.id}").json()["status"] == "confirmed"


def test_confirm_rejects_actions_not_in_card(ctx):
    clarify = {"kind": "speech", "transcript": "x", "summary_hi": None, "readback_hi": "कौन सा?",
               "actions": [{"tool": "clarify", "question_hi": "कौन सा?"}]}
    p = ready_input(ctx, clarify)
    forged = card()["actions"]
    assert ctx.c.post(f"/api/inputs/{p.id}/confirm", json={"actions": forged}).status_code == 422
    assert ctx.temporal.started == []
    oid = confirm_one(ctx)
    p2 = ready_input(ctx, {"kind": "speech", "transcript": "x", "summary_hi": None, "readback_hi": "…",
                           "actions": [{"tool": "mark_done", "obligation_id": oid, "title_hi": "…"}]})
    swapped = [{"tool": "mark_done", "obligation_id": "a-different-one"}]
    assert ctx.c.post(f"/api/inputs/{p2.id}/confirm", json={"actions": swapped}).status_code == 422
    p3 = ready_input(ctx)
    doubled = card()["actions"] * 2
    assert ctx.c.post(f"/api/inputs/{p3.id}/confirm", json={"actions": doubled}).status_code == 422


def test_confirm_takes_edits_but_keeps_the_card_evidence(ctx):
    p = ready_input(ctx)
    sent = [{**p.card["actions"][0], "amount_inr": 18500, "category": "other", "evidence_amount": "₹ 18,500"}]
    r = ctx.c.post(f"/api/inputs/{p.id}/confirm", json={"actions": sent, "role": "parent"})
    ob = asyncio.run(ctx.store.get_obligation(r.json()["results"][0]["obligation_id"]))
    assert ob["amount_inr"] == 18500                                   # the user's edit
    assert ob["category"] == "motor_insurance" and ob["evidence_amount"] == "₹ 18,400"   # from the card
    assert ob["source_input_id"] == p.id


def test_confirm_twice_returns_the_same_obligation(ctx):
    p = ready_input(ctx)
    body = {"actions": p.card["actions"], "role": "parent"}
    first = ctx.c.post(f"/api/inputs/{p.id}/confirm", json=body).json()
    second = ctx.c.post(f"/api/inputs/{p.id}/confirm", json=body).json()
    assert first == second
    assert len([s for s in ctx.temporal.started if s["workflow"] == "ObligationWorkflow.run"]) == 1
    assert len(ctx.c.get("/api/state").json()["obligations"]) == 1


def test_confirm_retry_after_a_crash_does_not_duplicate(ctx):
    p = ready_input(ctx)
    body = {"actions": p.card["actions"], "role": "parent"}
    ctx.temporal.fail_next_start = True
    with pytest.raises(RuntimeError):
        ctx.c.post(f"/api/inputs/{p.id}/confirm", json=body)   # saved, but the workflow didn't start
    r = ctx.c.post(f"/api/inputs/{p.id}/confirm", json=body)
    assert r.status_code == 200
    assert len(ctx.c.get("/api/state").json()["obligations"]) == 1
    assert ctx.temporal.started[-1]["id"] == f"obligation-{r.json()['results'][0]['obligation_id']}"


def test_confirm_without_date_is_rejected(ctx):
    p = ready_input(ctx, card(due=None))
    r = ctx.c.post(f"/api/inputs/{p.id}/confirm", json={"actions": p.card["actions"], "role": "parent"})
    assert r.status_code == 422 and "तारीख़" in r.json()["detail"]["hi"]


def test_confirm_requires_a_ready_input(ctx):
    p = ctx.app.state.inputs.create(ctx.hid, "parent", "text", text="x")
    assert ctx.c.post(f"/api/inputs/{p.id}/confirm", json={"actions": []}).status_code == 409


def test_done_twice_is_safe(ctx):
    oid = confirm_one(ctx)
    assert ctx.c.post(f"/api/obligations/{oid}/done", json={"role": "son"}).status_code == 200
    assert ctx.c.post(f"/api/obligations/{oid}/done", json={"role": "parent"}).status_code == 200
    assert [s[1] for s in ctx.temporal.signals] == ["mark_done"]
    ob = ctx.c.get("/api/state").json()["obligations"][0]
    assert ob["status"] == "done" and ob["next"] is None


def test_snooze_rules(ctx):
    oid = confirm_one(ctx)
    past = (date.today() - timedelta(days=1)).isoformat()
    assert ctx.c.post(f"/api/obligations/{oid}/snooze", json={"until": past}).status_code == 422
    after_due = (date.today() + timedelta(days=90)).isoformat()
    assert ctx.c.post(f"/api/obligations/{oid}/snooze", json={"until": after_due}).status_code == 200
    assert ctx.temporal.signals[-1][1:] == ("snooze", (after_due,))


def test_push_subscription(ctx):
    sub = {"endpoint": "https://push.example/1", "keys": {"p256dh": "a", "auth": "b"}}
    assert ctx.c.post("/api/push/subscribe", json={"role": "son", "subscription": sub}).status_code == 200
    hh = asyncio.run(ctx.store.get_household(ctx.hid))
    assert hh["members"]["son"]["push"] == [{**sub, "lang": "hi"}]     # no language given: Hindi
    ctx.c.post("/api/push/subscribe", json={"role": "son", "subscription": sub, "lang": "en"})
    assert asyncio.run(ctx.store.get_household(ctx.hid))["members"]["son"]["push"] == [{**sub, "lang": "en"}]
    bad = ctx.c.post("/api/push/subscribe", json={"role": "son", "subscription": {"keys": {}}})
    assert bad.status_code == 422


def test_inbox_and_mark_read(ctx):
    asyncio.run(ctx.store.db.notifications.insert_one({
        "_id": "escalation:o1:x", "household_id": ctx.hid, "to_role": "son", "obligation_id": "o1",
        "kind": "escalation", "text_hi": "पापा ने…", "text_en": "Papa hasn't…",
        "created_at": datetime.now(timezone.utc), "read_at": None}))
    assert ctx.c.get("/api/state?role=parent").json()["unread"] == 0
    son = ctx.c.get("/api/state?role=son").json()
    assert son["unread"] == 1 and son["inbox"][0]["kind"] == "escalation"
    assert ctx.c.post("/api/notifications/escalation:o1:x/read").status_code == 200
    assert ctx.c.get("/api/state?role=son").json()["unread"] == 0
    assert ctx.c.post("/api/notifications/nope/read").status_code == 404


def test_bad_role_is_rejected(ctx):
    assert ctx.c.get("/api/state?role=uncle").status_code == 422


def test_server_voice_off_in_browser_mode(ctx):
    assert ctx.c.post("/api/tts", json={"text": "नमस्ते"}).status_code == 404


def test_server_voice_is_rate_limited(ctx):
    ctx.app.state.tts = FakeTTS()
    codes = [ctx.c.post("/api/tts", json={"text": f"t{i}"}).status_code for i in range(41)]
    assert codes[:40] == [200] * 40 and codes[40] == 429


def test_new_households_do_not_get_around_the_global_ai_cap(ctx):
    ctx.app.state.global_limiter = HourlyLimiter(limit=3)
    for _ in range(2):
        assert ctx.c.post("/api/inputs", data={"kind": "text", "text": "q"}).status_code == 200
    other = {"Authorization": f"Bearer {ctx.c.post('/api/households').json()['token']}"}
    assert ctx.c.post("/api/inputs", data={"kind": "text", "text": "q"}, headers=other).status_code == 200
    assert ctx.c.post("/api/inputs", data={"kind": "text", "text": "q"}, headers=other).status_code == 429


def test_one_address_cannot_make_endless_households(ctx):
    ctx.app.state.household_ip_limiter = HourlyLimiter(limit=1)
    assert ctx.c.post("/api/households").status_code == 200
    assert ctx.c.post("/api/households").status_code == 429
    assert ctx.c.post("/api/households", headers={"X-Forwarded-For": "203.0.113.9"}).status_code == 200


def test_one_address_cannot_use_up_the_global_ai_cap(ctx):
    # Without this, ~14 households from one machine spend the global 200/hour and lock out every visitor.
    ctx.app.state.ip_limiter = HourlyLimiter(limit=2)
    other = {"Authorization": f"Bearer {ctx.c.post('/api/households').json()['token']}"}
    assert ctx.c.post("/api/inputs", data={"kind": "text", "text": "q"}).status_code == 200
    assert ctx.c.post("/api/inputs", data={"kind": "text", "text": "q"}, headers=other).status_code == 200
    assert ctx.c.post("/api/inputs", data={"kind": "text", "text": "q"}, headers=other).status_code == 429
    elsewhere = {**other, "X-Forwarded-For": "203.0.113.9, 10.0.0.1"}
    assert ctx.c.post("/api/inputs", data={"kind": "text", "text": "q"}, headers=elsewhere).status_code == 200


def test_tts_speaks_in_the_asked_language(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_MODE", "demo")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()
    tts = FakeTTS()
    app = create_app(store=mock_store(), temporal=FakeTemporal(), push=FakePush(), tts=tts, start_workers=False)
    with TestClient(app) as c:
        c.headers["Authorization"] = f"Bearer {c.post('/api/households').json()['token']}"
        assert c.post("/api/tts", json={"text": "Is that right?", "lang": "en"}).status_code == 200
        assert c.post("/api/tts", json={"text": "सही है?"}).status_code == 200
        assert c.post("/api/tts", json={"text": "x", "lang": "fr"}).status_code == 422
    assert tts.calls == [("Is that right?", "en"), ("सही है?", "hi")]


def test_failed_input_message_comes_in_both_languages(ctx):
    p = ctx.app.state.inputs.create(ctx.hid, "parent", "text", text="x")
    p.status, p.error = "failed", "Busy"
    m = ctx.c.get(f"/api/inputs/{p.id}").json()["message"]
    assert m == {"code": "busy", "en": "The AI is busy right now. Please try again in a little while.",
                 "hi": "AI अभी व्यस्त है — थोड़ी देर में फिर कोशिश करें।"}


def scam_card():
    c = card()
    c["scam"] = {"level": "warning", "signs": [{"sign": "personal_payment", "evidence": "pay to x@ybl", "strong": True,
                                                "en": "Asks you to pay a personal UPI ID, number or account",
                                                "hi": "किसी निजी UPI, नंबर या खाते में पैसे माँगता है"}]}
    c["actions"][0]["scam"] = c["scam"]
    return c


def test_warn_son_puts_one_warning_in_the_sons_inbox(ctx):
    p = ready_input(ctx, scam_card())
    assert ctx.c.post(f"/api/inputs/{p.id}/warn-son").status_code == 200
    assert ctx.c.post(f"/api/inputs/{p.id}/warn-son").status_code == 200    # a second tap adds nothing
    inbox = ctx.c.get("/api/state?role=son").json()["inbox"]
    assert [n["kind"] for n in inbox] == ["scam_warning"]
    assert "suspicious" in inbox[0]["text_en"] and "personal UPI" in inbox[0]["text_en"]
    assert ctx.c.get("/api/state?role=parent").json()["inbox"] == []


def test_warn_son_needs_a_warning_on_the_card(ctx):
    p = ready_input(ctx)
    r = ctx.c.post(f"/api/inputs/{p.id}/warn-son")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "no_warning"


def test_saving_anyway_keeps_the_warning_on_the_record(ctx):
    p = ready_input(ctx, scam_card())
    r = ctx.c.post(f"/api/inputs/{p.id}/confirm", json={"actions": p.card["actions"], "role": "parent"})
    ob = asyncio.run(ctx.store.get_obligation(r.json()["results"][0]["obligation_id"]))
    assert ob["scam"]["level"] == "warning"


def test_done_offers_next_year_and_repeat_adds_it(ctx):
    oid = confirm_one(ctx)            # the fixture card is motor insurance due in 70 days
    r = ctx.c.post(f"/api/obligations/{oid}/done", json={"role": "parent"}).json()
    offer = r["repeat_offer"]
    assert offer["obligation_id"] == oid and offer["due_date"][:4] == str(date.fromisoformat(DUE).year + 1)
    rep = ctx.c.post(f"/api/obligations/{oid}/repeat", json={"role": "parent"})
    assert rep.status_code == 200
    items = {o["id"]: o for o in ctx.c.get("/api/state").json()["obligations"]}
    new = items[rep.json()["obligation_id"]]
    assert new["amount_inr"] is None and new["last_amount_inr"] == 18400 and new["yearly"] is True
    assert new["repeat_of"] == oid and new["status"] == "active"


def test_repeat_before_done_is_refused(ctx):
    oid = confirm_one(ctx)
    r = ctx.c.post(f"/api/obligations/{oid}/repeat", json={"role": "parent"})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "not_done_yet"


def test_web_files_are_always_revalidated(ctx):
    r = ctx.c.get("/app.js")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-cache"
    assert "cache-control" not in ctx.c.get("/api/health").headers


def test_input_reports_its_stage(ctx):
    p = ctx.app.state.inputs.create(ctx.hid, "parent", "text", text="x")
    assert ctx.c.get(f"/api/inputs/{p.id}").json()["stage"] == "sent"


def test_several_frontend_addresses_may_call_the_api(monkeypatch, tmp_path):
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://kaagaz.onrender.com, https://kaagaz-bx24.onrender.com")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()
    app = create_app(store=mock_store(), temporal=FakeTemporal(), push=FakePush(), start_workers=False)
    with TestClient(app) as c:
        for origin in ("https://kaagaz.onrender.com", "https://kaagaz-bx24.onrender.com"):
            r = c.get("/api/health", headers={"Origin": origin})
            assert r.headers.get("access-control-allow-origin") == origin
        assert "access-control-allow-origin" not in c.get("/api/health", headers={"Origin": "https://evil.example"}).headers
    get_settings.cache_clear()
