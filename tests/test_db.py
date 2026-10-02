from datetime import datetime, timedelta, timezone

from app.db import DEMO_TTL, hash_token
from tests.fakes import mock_store

NOW = datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc)


async def test_demo_household_expires_and_token_is_hashed():
    store = mock_store()
    await store.ensure_indexes()
    token, hh = await store.create_household("demo", NOW)
    assert hh["expires_at"] == NOW + DEMO_TTL
    assert hh["token_hash"] == hash_token(token) and token not in str(hh)
    assert (await store.household_by_token(token))["_id"] == hh["_id"]
    assert await store.household_by_token("wrong") is None


async def test_real_household_never_expires():
    store = mock_store()
    _, hh = await store.create_household("real", NOW)
    assert hh["expires_at"] is None


async def test_ttl_indexes_on_every_demo_collection():
    store = mock_store()
    await store.ensure_indexes()
    for name in ("households", "obligations", "notifications", "tts_cache"):
        info = await store.db[name].index_information()
        assert any(v.get("expireAfterSeconds") == 0 for v in info.values()), name


async def test_push_subscriptions_add_dedupe_remove():
    store = mock_store()
    _, hh = await store.create_household("demo", NOW)
    sub = {"endpoint": "https://push.example/1", "keys": {"p256dh": "x", "auth": "y"}}
    await store.add_push(hh["_id"], "parent", sub)
    await store.add_push(hh["_id"], "parent", sub)
    got = await store.get_household(hh["_id"])
    assert got["members"]["parent"]["push"] == [sub]
    await store.remove_push(hh["_id"], sub["endpoint"])
    assert (await store.get_household(hh["_id"]))["members"]["parent"]["push"] == []


async def test_obligations_scoped_to_household_and_history():
    store = mock_store()
    oid = await store.insert_obligation({"_id": "o1", "household_id": "h1", "due_date": "2026-12-14",
                                         "status": "active", "history": []})
    assert await store.get_obligation(oid, "h2") is None
    await store.set_obligation(oid, {"status": "done"}, {"at": NOW, "by_role": "son", "event": "done"})
    ob = await store.get_obligation(oid, "h1")
    assert ob["status"] == "done" and ob["history"][0]["event"] == "done"


async def test_notifications_listing_and_read():
    store = mock_store()
    for i in range(3):
        await store.db.notifications.insert_one({"_id": f"n{i}", "household_id": "h1", "to_role": "parent",
                                                 "created_at": NOW + timedelta(minutes=i), "read_at": None})
    items = await store.list_notifications("h1", "parent")
    assert [n["_id"] for n in items] == ["n2", "n1", "n0"]
    assert await store.mark_read("h1", "n1", NOW) is True
    assert await store.mark_read("h2", "n0", NOW) is False


async def test_tts_cache_roundtrip():
    store = mock_store()
    assert await store.tts_get("k") is None
    await store.tts_put("k", b"mp3", NOW)
    assert await store.tts_get("k") == b"mp3"
