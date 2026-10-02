"""MongoDB access. Tests pass a mongomock database; production uses pymongo's async client."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta

DEMO_TTL = timedelta(hours=48)
TTS_TTL = timedelta(days=30)
ROLES = ("parent", "son")
# A TTL index doesn't cascade, so every collection holding demo data expires on its own field.
TTL_COLLECTIONS = ("households", "obligations", "notifications", "tts_cache")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_id() -> str:
    return uuid.uuid4().hex


class Store:
    def __init__(self, db):
        self.db = db

    async def ensure_indexes(self) -> None:
        for name in TTL_COLLECTIONS:
            await self.db[name].create_index("expires_at", expireAfterSeconds=0)
        await self.db.households.create_index("token_hash", unique=True)
        await self.db.obligations.create_index([("household_id", 1), ("due_date", 1)])
        await self.db.notifications.create_index([("household_id", 1), ("to_role", 1), ("created_at", -1)])

    # households
    async def create_household(self, mode: str, now: datetime) -> tuple[str, dict]:
        token = secrets.token_urlsafe(24)
        doc = {"_id": new_id(), "token_hash": hash_token(token), "mode": mode, "created_at": now,
               "expires_at": now + DEMO_TTL if mode == "demo" else None,
               "members": {"parent": {"name": "Papa", "push": []}, "son": {"name": "Beta", "push": []}}}
        await self.db.households.insert_one(doc)
        return token, doc

    async def household_by_token(self, token: str) -> dict | None:
        return await self.db.households.find_one({"token_hash": hash_token(token)})

    async def get_household(self, hid: str) -> dict | None:
        return await self.db.households.find_one({"_id": hid})

    async def add_push(self, hid: str, role: str, subscription: dict) -> None:
        path = f"members.{role}.push"
        await self.db.households.update_one({"_id": hid}, {"$pull": {path: {"endpoint": subscription["endpoint"]}}})
        await self.db.households.update_one({"_id": hid}, {"$push": {path: subscription}})

    async def remove_push(self, hid: str, endpoint: str) -> None:
        for role in ROLES:
            await self.db.households.update_one({"_id": hid}, {"$pull": {f"members.{role}.push": {"endpoint": endpoint}}})

    # obligations
    async def insert_obligation(self, doc: dict) -> str:
        await self.db.obligations.insert_one(doc)
        return doc["_id"]

    async def get_obligation(self, oid: str, hid: str | None = None) -> dict | None:
        query = {"_id": oid} if hid is None else {"_id": oid, "household_id": hid}
        return await self.db.obligations.find_one(query)

    async def set_obligation(self, oid: str, fields: dict, event: dict) -> None:
        await self.db.obligations.update_one({"_id": oid}, {"$set": fields, "$push": {"history": event}})

    async def list_obligations(self, hid: str) -> list[dict]:
        return await self.db.obligations.find({"household_id": hid}).sort("due_date", 1).to_list(None)

    # notifications
    async def list_notifications(self, hid: str, role: str, limit: int = 30) -> list[dict]:
        cursor = self.db.notifications.find({"household_id": hid, "to_role": role}).sort("created_at", -1)
        return await cursor.limit(limit).to_list(None)

    async def mark_read(self, hid: str, nid: str, now: datetime) -> bool:
        r = await self.db.notifications.update_one({"_id": nid, "household_id": hid}, {"$set": {"read_at": now}})
        return r.matched_count == 1

    # text-to-speech cache (shared across households, so it has its own expiry)
    async def tts_get(self, key: str) -> bytes | None:
        doc = await self.db.tts_cache.find_one({"_id": key})
        return bytes(doc["mp3"]) if doc else None

    async def tts_put(self, key: str, mp3: bytes, now: datetime) -> None:
        await self.db.tts_cache.replace_one({"_id": key}, {"_id": key, "mp3": mp3, "created_at": now,
                                                          "expires_at": now + TTS_TTL}, upsert=True)


def connect_store(settings) -> Store:
    from pymongo import AsyncMongoClient

    client = AsyncMongoClient(settings.mongodb_uri, tz_aware=True, serverSelectionTimeoutMS=15000)
    return Store(client[settings.mongodb_db])
