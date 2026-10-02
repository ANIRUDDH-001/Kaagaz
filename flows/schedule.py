"""When each reminder and the escalation fire. Pure and deterministic: the workflow
recomputes this on every loop, and the API uses it for the "next reminder" line."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.clock import at_ist

REAL_ESCALATION_DELAY = timedelta(hours=6)
REMINDER_HOUR_IST = 9


@dataclass(frozen=True)
class Point:
    id: str
    kind: str   # "reminder" | "escalation"
    label: str  # "d30" | "d7" | "d1" | "now" | "snooze" | "escalation"
    at: datetime


def plan_points(*, due: date, offsets: list[int], schedule: str, started_at: datetime,
                gap_seconds: int = 30, escalate: bool = True, snooze_until: date | None = None,
                snoozed_at: datetime | None = None) -> list[Point]:
    days = sorted({int(o) for o in offsets if int(o) > 0}, reverse=True) or [1]
    if schedule == "demo":
        gap = timedelta(seconds=gap_seconds)
        base = [Point(f"d{o}:{due}", "reminder", f"d{o}", started_at + gap * (i + 1))
                for i, o in enumerate(days)]
        escalation_delay = gap * 3
        snooze_at = snoozed_at + gap if snooze_until and snoozed_at else None
    elif schedule == "real":
        base = [Point(f"d{o}:{due}", "reminder", f"d{o}", at_ist(due - timedelta(days=o), REMINDER_HOUR_IST))
                for o in days]
        base = [p for p in base if p.at > started_at] or [Point(f"now:{due}", "reminder", "now", started_at)]
        escalation_delay = REAL_ESCALATION_DELAY
        snooze_at = at_ist(snooze_until, REMINDER_HOUR_IST) if snooze_until else None
    else:
        raise ValueError(f"unknown schedule {schedule!r}")

    points = list(base)
    if snooze_at is not None:
        points = [p for p in points if p.at >= snooze_at]
        points.append(Point(f"snooze:{snooze_until}", "reminder", "snooze", snooze_at))
    if escalate:
        last = max(p.at for p in base)
        points.append(Point(f"escalation:{due}", "escalation", "escalation", last + escalation_delay))
    return sorted(points, key=lambda p: (p.at, p.kind == "escalation"))


def next_point(ob: dict, mode: str, now: datetime, gap_seconds: int = 30) -> Point | None:
    if ob.get("status") != "active":
        return None
    snooze = ob.get("snoozed_until")
    points = plan_points(
        due=date.fromisoformat(ob["due_date"]), offsets=ob["remind_offsets_days"],
        schedule="demo" if mode == "demo" else "real", started_at=ob["created_at"],
        gap_seconds=gap_seconds, escalate=ob.get("escalate", True),
        snooze_until=date.fromisoformat(snooze) if snooze else None, snoozed_at=ob.get("snoozed_at"))
    return next((p for p in points if p.at > now), None)
