from datetime import date, datetime, timedelta, timezone

from flows.schedule import next_point, plan_points

UTC = timezone.utc
T0 = datetime(2026, 10, 2, 10, 0, tzinfo=UTC)


def ids(points):
    return [p.id for p in points]


def test_real_full_schedule_with_escalation():
    pts = plan_points(due=date(2026, 12, 14), offsets=[30, 7, 1], schedule="real", started_at=T0)
    assert ids(pts) == ["d30:2026-12-14", "d7:2026-12-14", "d1:2026-12-14", "escalation:2026-12-14"]
    assert pts[0].at == datetime(2026, 11, 14, 3, 30, tzinfo=UTC)   # 09:00 IST
    assert pts[2].at == datetime(2026, 12, 13, 3, 30, tzinfo=UTC)
    assert pts[3].at == datetime(2026, 12, 13, 9, 30, tzinfo=UTC)   # 15:00 IST on due - 1
    assert pts[3].kind == "escalation"


def test_real_skips_points_already_past():
    pts = plan_points(due=date(2026, 10, 10), offsets=[30, 7, 1], schedule="real", started_at=T0)
    assert ids(pts) == ["d7:2026-10-10", "d1:2026-10-10", "escalation:2026-10-10"]


def test_real_all_past_gives_one_reminder_now():
    started = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)
    pts = plan_points(due=date(2026, 10, 3), offsets=[30, 7, 1], schedule="real", started_at=started)
    assert ids(pts) == ["now:2026-10-03", "escalation:2026-10-03"]
    assert pts[0].at == started
    assert pts[1].at == started + timedelta(hours=6)


def test_demo_schedule_is_compressed():
    pts = plan_points(due=date(2026, 12, 14), offsets=[30, 7, 1], schedule="demo", started_at=T0)
    assert [(p.label, (p.at - T0).total_seconds()) for p in pts] == [
        ("d30", 30), ("d7", 60), ("d1", 90), ("escalation", 180)]


def test_demo_snooze_drops_earlier_reminders_and_keeps_escalation():
    pts = plan_points(due=date(2026, 12, 14), offsets=[30, 7, 1], schedule="demo", started_at=T0,
                      snooze_until=date(2026, 10, 9), snoozed_at=T0 + timedelta(seconds=70))
    assert [(p.label, (p.at - T0).total_seconds()) for p in pts] == [
        ("snooze", 100), ("escalation", 180)]


def test_real_snooze_adds_point_and_keeps_later_reminders():
    pts = plan_points(due=date(2026, 12, 14), offsets=[30, 7, 1], schedule="real", started_at=T0,
                      snooze_until=date(2026, 10, 9), snoozed_at=T0)
    assert ids(pts) == ["snooze:2026-10-09", "d30:2026-12-14", "d7:2026-12-14", "d1:2026-12-14",
                        "escalation:2026-12-14"]


def test_no_escalation_when_disabled():
    pts = plan_points(due=date(2026, 12, 14), offsets=[7], schedule="real", started_at=T0, escalate=False)
    assert ids(pts) == ["d7:2026-12-14"]


def test_custom_gap_for_infra_proof():
    pts = plan_points(due=date(2026, 12, 14), offsets=[1], schedule="demo", started_at=T0,
                      gap_seconds=1200, escalate=False)
    assert pts[0].at == T0 + timedelta(minutes=20)


def test_next_point_for_active_obligation():
    ob = {"status": "active", "due_date": "2026-12-14", "remind_offsets_days": [30, 7, 1],
          "created_at": T0, "escalate": True, "snoozed_until": None, "snoozed_at": None}
    p = next_point(ob, "real", T0 + timedelta(days=1))
    assert p.id == "d30:2026-12-14"
    assert next_point({**ob, "status": "done"}, "real", T0) is None
