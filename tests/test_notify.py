import asyncio
from datetime import datetime, timedelta, timezone

from flows.notify import Notification, deliver
from flows.push import topic_for
from tests.fakes import FakePush, mock_store

NOW = datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc)
SUB = {"endpoint": "https://push.example/1", "keys": {"p256dh": "x", "auth": "y"}}


async def setup(with_sub=True):
    store = mock_store()
    await store.ensure_indexes()
    _, hh = await store.create_household("demo", NOW)
    if with_sub:
        await store.add_push(hh["_id"], "parent", SUB)
    n = Notification(id="reminder:o1:d7:2026-12-14", household_id=hh["_id"], to_role="parent", obligation_id="o1",
                     kind="reminder", point="d7:2026-12-14", text_hi="नमस्ते", text_en="hello",
                     expires_at=hh["expires_at"])
    return store, hh, n


async def test_retry_creates_one_record_and_one_push():
    store, _, n = await setup()
    push = FakePush()
    assert await deliver(store, push, n, NOW) == "sent"
    assert await deliver(store, push, n, NOW + timedelta(seconds=5)) == "already-handled"
    assert await store.db.notifications.count_documents({}) == 1
    assert len(push.calls) == 1
    endpoint, payload, topic = push.calls[0]
    assert payload == {"title": "काग़ज़ · Kaagaz", "body": "नमस्ते", "tag": n.id, "role": "parent"}
    assert topic == topic_for(n.id) and len(topic) == 32


async def test_two_workers_at_once_push_once():
    store, _, n = await setup()
    push = FakePush()
    results = await asyncio.gather(deliver(store, push, n, NOW), deliver(store, push, n, NOW))
    assert sorted(results) == ["already-handled", "sent"]
    assert await store.db.notifications.count_documents({}) == 1
    assert len(push.calls) == 1


async def test_inbox_record_exists_without_any_push_subscription():
    store, _, n = await setup(with_sub=False)
    push = FakePush()
    assert await deliver(store, push, n, NOW) == "sent"
    doc = await store.db.notifications.find_one({"_id": n.id})
    assert doc["text_hi"] == "नमस्ते" and doc["read_at"] is None and doc["expires_at"] == n.expires_at
    assert push.calls == []


async def test_gone_subscription_is_removed():
    store, hh, n = await setup()
    await deliver(store, FakePush(result="gone"), n, NOW)
    assert (await store.get_household(hh["_id"]))["members"]["parent"]["push"] == []


async def test_push_failure_still_counts_as_delivered():
    store, _, n = await setup()
    assert await deliver(store, FakePush(result="error"), n, NOW) == "sent"
    assert (await store.db.notifications.find_one({"_id": n.id}))["push_sent_at"] == NOW


async def test_stale_claim_is_retried_after_lease():
    store, _, n = await setup()
    push = FakePush()
    await deliver(store, push, n, NOW)
    # simulate a crash after claiming but before pushing
    await store.db.notifications.update_one({"_id": n.id}, {"$set": {"push_sent_at": None,
                                                                    "push_claimed_at": NOW}})
    assert await deliver(store, push, n, NOW + timedelta(seconds=30)) == "already-handled"
    assert await deliver(store, push, n, NOW + timedelta(seconds=61)) == "sent"
    assert len(push.calls) == 2


async def test_each_phone_gets_the_text_in_its_language():
    store, hh, n = await setup(with_sub=False)
    await store.add_push(hh["_id"], "parent", {**SUB, "lang": "en"})
    await store.add_push(hh["_id"], "parent", {"endpoint": "https://push.example/2", "keys": SUB["keys"], "lang": "hi"})
    push = FakePush()
    await deliver(store, push, n, NOW)
    assert sorted((e, p["body"]) for e, p, _ in push.calls) == [("https://push.example/1", "hello"),
                                                                 ("https://push.example/2", "नमस्ते")]
