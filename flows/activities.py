"""Reminder activities. They need only MongoDB and the push key (no AI), so the
GitHub Actions worker can run them while Render sleeps."""
from dataclasses import dataclass

from temporalio import activity

from app.clock import now_utc, today_ist
from flows.messages import escalation_text, reminder_text
from flows.notify import Notification, deliver


@dataclass
class NotifyArgs:
    obligation_id: str
    household_id: str
    point_id: str
    label: str


class ReminderActivities:
    def __init__(self, store, push, clock=now_utc):
        self.store = store
        self.push = push
        self.clock = clock

    async def _send(self, a: NotifyArgs, kind: str) -> str:
        ob = await self.store.get_obligation(a.obligation_id)
        if not ob or ob.get("status") != "active":
            return "skipped"
        household = await self.store.get_household(a.household_id) or {}
        now = self.clock()
        today = today_ist(now)
        if kind == "reminder":
            hi, en = reminder_text(ob, a.label, today, demo=household.get("mode") == "demo")
            role = "parent"
        else:
            hi, en = escalation_text(ob, today)
            role = "son"
        n = Notification(id=f"{kind}:{a.obligation_id}:{a.point_id}", household_id=a.household_id, to_role=role,
                         obligation_id=a.obligation_id, kind=kind, point=a.point_id, text_hi=hi, text_en=en,
                         expires_at=household.get("expires_at"))
        return await deliver(self.store, self.push, n, now)

    @activity.defn
    async def send_reminder(self, a: NotifyArgs) -> str:
        return await self._send(a, "reminder")

    @activity.defn
    async def send_escalation(self, a: NotifyArgs) -> str:
        return await self._send(a, "escalation")
