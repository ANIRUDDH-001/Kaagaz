import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from flows.activities import ReminderActivities
from flows.obligation_workflow import ObligationArgs, ObligationWorkflow
from tests.fakes import FakePush, mock_store

Q = "test-reminders"


@pytest.fixture
async def env():
    async with await WorkflowEnvironment.start_time_skipping() as e:
        yield e


async def make(store, mode, due):
    _, hh = await store.create_household(mode, datetime.now(timezone.utc))
    oid = uuid.uuid4().hex
    await store.insert_obligation({"_id": oid, "household_id": hh["_id"], "title": "Car insurance renewal",
                                   "title_hi": "गाड़ी का इंश्योरेंस", "amount_inr": 18400,
                                   "due_date": due.isoformat(), "status": "active", "history": [],
                                   "expires_at": hh["expires_at"]})
    return hh, oid


def worker(env, store, push):
    acts = ReminderActivities(store, push)
    return Worker(env.client, task_queue=Q, workflows=[ObligationWorkflow],
                  activities=[acts.send_reminder, acts.send_escalation])


async def notes(store, oid):
    return await store.db.notifications.find({"obligation_id": oid}).sort("created_at", 1).to_list(None)


async def test_ignored_real_obligation_gets_three_reminders_then_escalation(env):
    store, push = mock_store(), FakePush()
    due = date.today() + timedelta(days=40)
    hh, oid = await make(store, "real", due)
    async with worker(env, store, push):
        result = await env.client.execute_workflow(
            ObligationWorkflow.run, ObligationArgs(oid, hh["_id"], due.isoformat(), [30, 7, 1], "real"),
            id=f"ob-{oid}", task_queue=Q)
    assert result == "finished"
    got = await notes(store, oid)
    assert [(n["kind"], n["to_role"]) for n in got] == [
        ("reminder", "parent"), ("reminder", "parent"), ("reminder", "parent"), ("escalation", "son")]
    assert got[0]["_id"] == f"reminder:{oid}:d30:{due}"


async def test_mark_done_stops_everything(env):
    store, push = mock_store(), FakePush()
    due = date.today() + timedelta(days=40)
    hh, oid = await make(store, "real", due)
    async with worker(env, store, push):
        handle = await env.client.start_workflow(
            ObligationWorkflow.run, ObligationArgs(oid, hh["_id"], due.isoformat(), [30, 7, 1], "real"),
            id=f"ob-{oid}", task_queue=Q)
        await env.sleep(timedelta(days=11))          # d30 (day ~10) has fired
        await handle.signal(ObligationWorkflow.mark_done)
        assert await handle.result() == "done"
    assert len(await notes(store, oid)) == 1


async def test_demo_schedule_runs_in_minutes(env):
    store, push = mock_store(), FakePush()
    due = date.today() + timedelta(days=60)
    hh, oid = await make(store, "demo", due)
    async with worker(env, store, push):
        result = await env.client.execute_workflow(
            ObligationWorkflow.run, ObligationArgs(oid, hh["_id"], due.isoformat(), [30, 7, 1], "demo"),
            id=f"ob-{oid}", task_queue=Q)
    got = await notes(store, oid)
    assert result == "finished" and len(got) == 4
    assert got[0]["text_hi"].startswith("(30 दिन पहले वाला reminder)")
    assert got[-1]["kind"] == "escalation"


async def test_snooze_adds_a_reminder_on_that_date(env):
    store, push = mock_store(), FakePush()
    due = date.today() + timedelta(days=40)
    hh, oid = await make(store, "real", due)
    async with worker(env, store, push):
        handle = await env.client.start_workflow(
            ObligationWorkflow.run, ObligationArgs(oid, hh["_id"], due.isoformat(), [30, 7, 1], "real"),
            id=f"ob-{oid}", task_queue=Q)
        await env.sleep(timedelta(days=11))
        until = date.today() + timedelta(days=15)
        await handle.signal(ObligationWorkflow.snooze, until.isoformat())
        assert await handle.result() == "finished"
    ids = [n["_id"] for n in await notes(store, oid)]
    assert f"reminder:{oid}:snooze:{until}" in ids
    assert len(ids) == 5   # d30, snooze, d7, d1, escalation


async def test_obligation_done_in_db_but_not_signalled_sends_nothing(env):
    store, push = mock_store(), FakePush()
    due = date.today() + timedelta(days=60)
    hh, oid = await make(store, "demo", due)
    await store.set_obligation(oid, {"status": "done"}, {"event": "done"})
    async with worker(env, store, push):
        await env.client.execute_workflow(
            ObligationWorkflow.run, ObligationArgs(oid, hh["_id"], due.isoformat(), [30, 7, 1], "demo"),
            id=f"ob-{oid}", task_queue=Q)
    assert await notes(store, oid) == []


class FlakyStore:
    """Wraps the store; the first `fails` reads of an obligation raise, like MongoDB being unreachable."""

    def __init__(self, inner, fails: int):
        self.inner = inner
        self.fails = fails

    def __getattr__(self, name):
        return getattr(self.inner, name)

    async def get_obligation(self, *args):
        if self.fails > 0:
            self.fails -= 1
            raise RuntimeError("database unreachable")
        return await self.inner.get_obligation(*args)


async def test_transient_failure_is_retried_and_sent_once(env):
    store, push = mock_store(), FakePush()
    due = date.today() + timedelta(days=60)
    hh, oid = await make(store, "demo", due)
    async with worker(env, FlakyStore(store, fails=3), push):
        handle = await env.client.start_workflow(
            ObligationWorkflow.run, ObligationArgs(oid, hh["_id"], due.isoformat(), [30, 7, 1], "demo"),
            id=f"ob-{oid}", task_queue=Q)
        assert await handle.result() == "finished"
        progress = await handle.query(ObligationWorkflow.progress)
    assert len(await notes(store, oid)) == 4
    assert len(progress["sent"]) == 4 and progress["failed"] == []


async def test_failed_reminder_is_not_counted_as_sent(env):
    store, push = mock_store(), FakePush()
    due = date.today() + timedelta(days=60)
    hh, oid = await make(store, "demo", due)
    async with worker(env, FlakyStore(store, fails=10**6), push):
        handle = await env.client.start_workflow(
            ObligationWorkflow.run, ObligationArgs(oid, hh["_id"], due.isoformat(), [30, 7, 1], "demo"),
            id=f"ob-{oid}", task_queue=Q)
        assert await handle.result() == "finished"
        progress = await handle.query(ObligationWorkflow.progress)
    assert progress["sent"] == [] and len(progress["failed"]) == 4
    assert await notes(store, oid) == []
