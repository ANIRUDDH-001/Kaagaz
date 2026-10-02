"""Time helpers. India has no DST, so IST is a fixed offset (no tz database needed on Windows)."""
from datetime import date, datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30), "IST")
HINDI_MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून",
                "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
ENGLISH_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def today_ist(now: datetime | None = None) -> date:
    return (now or now_utc()).astimezone(IST).date()


def today_label(d: date) -> str:
    return f"{d.isoformat()} ({WEEKDAYS[d.weekday()]})"


def at_ist(d: date, hour: int) -> datetime:
    return datetime.combine(d, time(hour), IST).astimezone(timezone.utc)


def english_date(d: date, with_year: bool = False) -> str:
    s = f"{d.day} {ENGLISH_MONTHS[d.month - 1]}"
    return f"{s} {d.year}" if with_year else s


def hindi_date(d: date, with_year: bool = False) -> str:
    s = f"{d.day} {HINDI_MONTHS[d.month - 1]}"
    return f"{s} {d.year}" if with_year else s
