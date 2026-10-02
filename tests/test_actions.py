from datetime import datetime, timedelta, timezone

import pytest
from temporalio.service import RPCError, RPCStatusCode

from app.actions import ActionError, mark_done, snooze, update_obligation
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
    with pytest.raises(ActionError):
        await snooze(store, temporal, ob, "2026-10-09", "son", NOW)
    assert (await store.get_obligation("ob1", hh["_id"]))["snoozed_until"] is None


async def test_snooze_during_a_temporal_blip_asks_to_retry_and_saves_nothing():
    store, temporal, hh, ob = await setup()
    temporal.signal_error = rpc(RPCStatusCode.UNAVAILABLE)
    with pytest.raises(ActionError):
        await snooze(store, temporal, ob, "2026-10-09", "son", NOW)
    assert (await store.get_obligation("ob1", hh["_id"]))["snoozed_until"] is None


async def test_mark_done_on_a_closed_workflow_still_counts():
    store, temporal, hh, ob = await setup()
    temporal.signal_error = rpc(RPCStatusCode.NOT_FOUND)
    await mark_done(store, temporal, ob, "parent", NOW)
    assert (await store.get_obligation("ob1", hh["_id"]))["status"] == "done"


@pytest.mark.parametrize("bad", ["2026-01-01", "2029-01-01"])
async def test_update_rejects_a_date_create_would_reject(bad):
    store, temporal, hh, ob = await setup()
    with pytest.raises(ActionError):
        await update_obligation(store, temporal, ob, {"due_date": bad}, "parent", NOW)
    assert temporal.signals == []


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
