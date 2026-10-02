"""Write a notification exactly once, then push it at most once per lease.

Temporal may run an activity more than once (retry after a crash, two workers racing),
so the record's _id is deterministic and push is guarded by an atomic claim."""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

from pymongo.errors import DuplicateKeyError

from flows.push import topic_for

CLAIM_LEASE = timedelta(seconds=60)


@dataclass
class Notification:
    id: str
    household_id: str
    to_role: str
    obligation_id: str
    kind: str
    point: str
    text_hi: str
    text_en: str
    expires_at: datetime | None


async def deliver(store, push, n: Notification, now: datetime) -> str:
    doc = asdict(n)
    doc["_id"] = doc.pop("id")
    doc.update(created_at=now, push_claimed_at=None, push_sent_at=None, read_at=None)
    try:
        await store.db.notifications.insert_one(doc)
    except DuplicateKeyError:
        pass

    claim = await store.db.notifications.update_one(
        {"_id": n.id, "push_sent_at": None,
         "$or": [{"push_claimed_at": None}, {"push_claimed_at": {"$lt": now - CLAIM_LEASE}}]},
        {"$set": {"push_claimed_at": now}})
    if claim.modified_count == 0:
        return "already-handled"

    household = await store.get_household(n.household_id) or {}
    subscriptions = household.get("members", {}).get(n.to_role, {}).get("push", [])
    payload = {"title": "काग़ज़ · Kaagaz", "body": n.text_hi, "tag": n.id, "role": n.to_role}
    for sub in subscriptions:
        if await push.send(sub, payload, topic_for(n.id)) == "gone":
            await store.remove_push(n.household_id, sub["endpoint"])
    await store.db.notifications.update_one({"_id": n.id}, {"$set": {"push_sent_at": now}})
    return "sent"
