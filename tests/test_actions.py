from datetime import date, datetime, timedelta, timezone

import pytest
from temporalio.service import RPCError, RPCStatusCode

from app.actions import (ActionError, mark_done, next_year_due, repeat_obligation, repeat_offer, snooze,
                         update_obligation)
from tests.fakes import FakeTemporal, mock_store

NOW = datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc)


async def setup():
    store, temporal = mock_store(), FakeTemporal()
    _, hh = await store.create_household("real", NOW)
    ob = {"_id": "ob1", "household_id": hh["_id"], "title": "Car insurance", "due_date": "2026-12-14",
          "status": "active", "workflow_id": "obligation-ob1", "snoozed_until": None, "history": []}
    await store.insert_obligation(ob)
    return store, temporal, hh, ob


def rpc(status):
    return RPCError("boom", status, b"")


async def test_snooze_on_a_closed_workflow_says_so_and_saves_nothing():
    store, temporal, hh, ob = await setup()
    temporal.signal_error = rpc(RPCStatusCode.NOT_FOUND)
    with pytest.raises(ActionError) as e:
        await snooze(store, temporal, ob, "2026-10-09", "son", NOW)
    assert (await store.get_obligation("ob1", hh["_id"]))["snoozed_until"] is None
    assert e.value.code == "reminders_closed"


async def test_snooze_during_a_temporal_blip_asks_to_retry_and_saves_nothing():
    store, temporal, hh, ob = await setup()
    temporal.signal_error = rpc(RPCStatusCode.UNAVAILABLE)
    with pytest.raises(ActionError) as e:
        await snooze(store, temporal, ob, "2026-10-09", "son", NOW)
    assert (await store.get_obligation("ob1", hh["_id"]))["snoozed_until"] is None
    assert e.value.code == "try_later"


async def test_mark_done_on_a_closed_workflow_still_counts():
    store, temporal, hh, ob = await setup()
    temporal.signal_error = rpc(RPCStatusCode.NOT_FOUND)
    await mark_done(store, temporal, ob, "parent", NOW)
    assert (await store.get_obligation("ob1", hh["_id"]))["status"] == "done"


@pytest.mark.parametrize("bad", ["2026-01-01", "2029-01-01"])
async def test_update_rejects_a_date_create_would_reject(bad):
    store, temporal, hh, ob = await setup()
    with pytest.raises(ActionError) as e:
        await update_obligation(store, temporal, ob, {"due_date": bad}, "parent", NOW)
    assert temporal.signals == []
    assert e.value.code == "date_wrong"


async def test_update_records_when_the_date_changed():
    store, temporal, hh, ob = await setup()
    await update_obligation(store, temporal, ob, {"due_date": "2026-12-16"}, "parent", NOW)
    saved = await store.get_obligation("ob1", hh["_id"])
    assert saved["due_date"] == "2026-12-16" and saved["due_changed_at"] == NOW
    assert temporal.signals == [("obligation-ob1", "update_due", ("2026-12-16",))]


async def test_mark_done_during_a_temporal_blip_still_counts():
    # Reminders check the database before sending, so "done" never needs the workflow to hear it.
    store, temporal, hh, ob = await setup()
    temporal.signal_error = rpc(RPCStatusCode.UNAVAILABLE)
    await mark_done(store, temporal, ob, "parent", NOW)
    assert (await store.get_obligation("ob1", hh["_id"]))["status"] == "done"


def done_motor(**kw):
    return {"_id": "ob1", "household_id": "h1", "title": "Car insurance renewal", "title_hi": "गाड़ी का बीमा",
            "category": "motor_insurance", "amount_inr": 18400.0, "due_date": "2026-12-14", "action": "Renew",
            "consequence": None, "evidence_amount": "₹ 18,400", "evidence_due_date": "14/12/2026",
            "evidence_consequence": None, "summary_hi": None, "remind_offsets_days": [30, 7, 1], "escalate": True,
            "source": "photo", "scam": None, "status": "done", "workflow_id": "obligation-ob1", "history": [], **kw}


HH = {"_id": "h1", "mode": "demo", "expires_at": None}


def test_next_year_due_rolls_to_the_first_future_anniversary():
    today = date(2026, 10, 2)
    assert next_year_due(date(2026, 12, 14), today) == date(2027, 12, 14)
    assert next_year_due(date(2024, 3, 1), today) == date(2027, 3, 1)      # long ago: first future one
    assert next_year_due(date(2028, 2, 29), today) == date(2029, 2, 28)    # leap day


def test_only_yearly_papers_get_a_repeat_offer():
    today = date(2026, 10, 2)
    assert repeat_offer(done_motor(), today) == {"obligation_id": "ob1", "due_date": "2027-12-14"}
    assert repeat_offer(done_motor(category="electricity_bill"), today) is None


async def test_mark_done_returns_the_repeat_offer():
    store, temporal = mock_store(), FakeTemporal()
    ob = done_motor(status="active")
    await store.insert_obligation(ob)
    assert await mark_done(store, temporal, ob, "parent", NOW) == {"obligation_id": "ob1", "due_date": "2027-12-14"}


async def test_repeat_makes_next_years_reminder_without_guessing_the_amount():
    store, temporal = mock_store(), FakeTemporal()
    await store.insert_obligation(done_motor())
    r = await repeat_obligation(store, temporal, HH, done_motor(), "parent", NOW)
    new = await store.get_obligation(r["obligation_id"])
    assert r == {"ok": True, "obligation_id": "ob1-y2027", "due_date": "2027-12-14"}
    assert new["amount_inr"] is None and new["last_amount_inr"] == 18400.0 and new["repeat_of"] == "ob1"
    assert new["status"] == "active" and new["evidence_amount"] is None and new["title"] == "Car insurance renewal"
    assert [s["id"] for s in temporal.started] == ["obligation-ob1-y2027"]
    assert temporal.started[0]["arg"].due_date == "2027-12-14"


async def test_a_double_tap_repeats_once():
    store, temporal = mock_store(), FakeTemporal()
    await store.insert_obligation(done_motor())
    await repeat_obligation(store, temporal, HH, done_motor(), "parent", NOW)
    await repeat_obligation(store, temporal, HH, done_motor(), "parent", NOW)
    assert await store.db.obligations.count_documents({"repeat_of": "ob1"}) == 1
    assert len(temporal.started) == 1


async def test_repeat_needs_a_done_yearly_paper():
    store, temporal = mock_store(), FakeTemporal()
    with pytest.raises(ActionError) as e:
        await repeat_obligation(store, temporal, HH, done_motor(status="active"), "parent", NOW)
    assert e.value.code == "not_done_yet"
    with pytest.raises(ActionError) as e:
        await repeat_obligation(store, temporal, HH, done_motor(category="electricity_bill"), "parent", NOW)
    assert e.value.code == "not_yearly"
