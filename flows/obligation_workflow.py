"""One workflow per obligation: sleeps until each reminder point, sends it, escalates if
ignored. Inputs and signals carry only IDs and dates; content stays in MongoDB."""
import asyncio
from dataclasses import dataclass
from datetime import date, timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from flows.activities import NotifyArgs, ReminderActivities
    from flows.schedule import plan_points

# No attempt limit: a reminder keeps retrying (backoff capped at 15 min) until it is delivered or
# its give-up window closes. Push errors never fail the activity (the inbox is canonical), so
# failures here mean MongoDB is unreachable.
NOTIFY_RETRY = RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=2.0,
                           maximum_interval=timedelta(minutes=15), maximum_attempts=0)
GIVE_UP = {"real": timedelta(hours=24), "demo": timedelta(minutes=10)}
# After its last point the workflow stays open this long, so a snooze or a new date (for example the son
# snoozing after he's been told) still lands.
KEEP_OPEN = {"real": timedelta(days=30), "demo": timedelta(minutes=10)}


@dataclass
class ObligationArgs:
    obligation_id: str
    household_id: str
    due_date: str
    offsets: list[int]
    schedule: str            # "real" | "demo"
    escalate: bool = True
    gap_seconds: int = 30    # demo only


@workflow.defn
class ObligationWorkflow:
    def __init__(self) -> None:
        self._due: date | None = None
        self._done = False
        self._cancelled = False
        self._changed = False
        self._snooze_until: date | None = None
        self._snoozed_at = None
        self._due_changed_at = None
        self._sent: list[str] = []
        self._failed: list[str] = []

    @workflow.run
    async def run(self, a: ObligationArgs) -> str:
        self._due = date.fromisoformat(a.due_date)
        started = workflow.now()
        while True:
            points = plan_points(due=self._due, offsets=a.offsets, schedule=a.schedule, started_at=started,
                                 gap_seconds=a.gap_seconds, escalate=a.escalate,
                                 snooze_until=self._snooze_until, snoozed_at=self._snoozed_at,
                                 changed_at=self._due_changed_at)
            pending = [p for p in points if p.id not in self._sent and p.id not in self._failed]
            point = pending[0] if pending else None
            self._changed = False
            wake = point.at if point else max(p.at for p in points) + KEEP_OPEN[a.schedule]
            delay = wake - workflow.now()
            if delay > timedelta(0):
                try:
                    await workflow.wait_condition(lambda: self._done or self._cancelled or self._changed,
                                                  timeout=delay)
                except asyncio.TimeoutError:
                    pass
            if self._done:
                return "done"
            if self._cancelled:
                return "cancelled"
            if self._changed:
                continue
            if point is None:
                return "finished"
            method = (ReminderActivities.send_escalation if point.kind == "escalation"
                      else ReminderActivities.send_reminder)
            try:
                await workflow.execute_activity_method(
                    method, NotifyArgs(a.obligation_id, a.household_id, point.id, point.label),
                    start_to_close_timeout=timedelta(seconds=60), schedule_to_close_timeout=GIVE_UP[a.schedule],
                    retry_policy=NOTIFY_RETRY)
            except ActivityError:
                # Failed is not sent. Record it and move on, so later reminders and the escalation still go out.
                workflow.logger.error("could not deliver %s for %s", point.id, a.obligation_id)
                self._failed.append(point.id)
                continue
            self._sent.append(point.id)   # "sent", "already-handled" or "skipped"

    @workflow.query
    def progress(self) -> dict:
        return {"sent": list(self._sent), "failed": list(self._failed)}

    @workflow.signal
    def mark_done(self) -> None:
        self._done = True

    @workflow.signal
    def cancel(self) -> None:
        self._cancelled = True

    @workflow.signal
    def snooze(self, until: str) -> None:
        self._snooze_until = date.fromisoformat(until)
        self._snoozed_at = workflow.now()
        self._changed = True

    @workflow.signal
    def update_due(self, due_date: str) -> None:
        self._due = date.fromisoformat(due_date)
        self._due_changed_at = workflow.now()
        self._changed = True
