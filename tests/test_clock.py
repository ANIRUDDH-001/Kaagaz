from datetime import date, datetime, timezone

from app.clock import at_ist, english_date, hindi_date, today_ist, today_label


def test_at_ist_converts_9am_ist_to_utc():
    assert at_ist(date(2026, 12, 13), 9) == datetime(2026, 12, 13, 3, 30, tzinfo=timezone.utc)


def test_today_ist_rolls_over_at_ist_midnight():
    late_utc = datetime(2026, 10, 2, 19, 0, tzinfo=timezone.utc)  # 00:30 IST on 3 Oct
    assert today_ist(late_utc) == date(2026, 10, 3)


def test_today_label():
    assert today_label(date(2026, 10, 2)) == "2026-10-02 (Friday)"


def test_hindi_date():
    assert hindi_date(date(2026, 12, 14)) == "14 दिसंबर"
    assert hindi_date(date(2027, 3, 31), with_year=True) == "31 मार्च 2027"


def test_english_date_is_short_and_locale_free():
    assert english_date(date(2026, 12, 14)) == "14 Dec"
    assert english_date(date(2026, 10, 9), with_year=True) == "9 Oct 2026"
