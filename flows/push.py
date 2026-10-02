"""Web Push. Best-effort delivery channel: the inbox record is the source of truth."""
import asyncio
import hashlib
import json
from typing import Protocol


class PushSender(Protocol):
    async def send(self, subscription: dict, payload: dict, topic: str) -> str: ...


def topic_for(notif_id: str) -> str:
    # Topic header: <= 32 URL-safe chars. A re-sent push with the same Topic replaces the undelivered one.
    return hashlib.sha256(notif_id.encode()).hexdigest()[:32]


class WebPushSender:
    def __init__(self, private_key: str, subject: str):
        self.private_key = private_key
        self.subject = subject

    async def send(self, subscription: dict, payload: dict, topic: str) -> str:
        if not self.private_key:
            return "error"
        from pywebpush import WebPushException, webpush

        def _send():
            webpush(subscription_info=subscription, data=json.dumps(payload, ensure_ascii=False),
                    vapid_private_key=self.private_key, vapid_claims={"sub": self.subject},
                    ttl=86400, headers={"Topic": topic, "Urgency": "high"})

        try:
            await asyncio.to_thread(_send)
            return "ok"
        except WebPushException as e:
            code = e.response.status_code if e.response is not None else None
            return "gone" if code in (404, 410) else "error"
        except Exception:  # noqa: BLE001  push is best-effort
            return "error"
