"""Reminder texts, written from stored fields by template (no model call, nothing invented)."""
from datetime import date

from app.clock import hindi_date

DEMO_LABEL = {"d30": "30 दिन पहले वाला reminder", "d7": "7 दिन पहले वाला reminder",
              "d1": "1 दिन पहले वाला reminder", "snooze": "आपका बताया हुआ reminder"}


def inr(amount: float | None) -> str:
    if amount is None:
        return ""
    s = str(int(round(float(amount))))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return f"₹{s}"


def _when_hi(days: int) -> str:
    if days < 0:
        return f"आख़िरी तारीख़ {-days} दिन पहले निकल चुकी है"
    if days == 0:
        return "आज आख़िरी दिन है"
    if days == 1:
        return "कल आख़िरी दिन है"
    return f"{days} दिन बचे हैं"


def _when_en(days: int) -> str:
    if days < 0:
        return f"{-days} days overdue"
    if days == 0:
        return "due today"
    return "1 day left" if days == 1 else f"{days} days left"


def reminder_text(ob: dict, label: str, today: date, demo: bool) -> tuple[str, str]:
    due = date.fromisoformat(ob["due_date"])
    days = (due - today).days
    amount = inr(ob.get("amount_inr"))
    title_hi = ob.get("title_hi") or ob["title"]
    head_hi = f"{title_hi}, {amount}" if amount else title_hi
    head_en = f"{ob['title']}, {amount}" if amount else ob["title"]
    hi = f"{head_hi} — आख़िरी तारीख़ {hindi_date(due)}, {_when_hi(days)}।"
    en = f"{head_en} — due {due:%d %b %Y} ({_when_en(days)})."
    if demo and label in DEMO_LABEL:
        hi = f"({DEMO_LABEL[label]}) {hi}"
    return hi, en


def escalation_text(ob: dict, today: date) -> tuple[str, str]:
    due = date.fromisoformat(ob["due_date"])
    amount = inr(ob.get("amount_inr"))
    title_hi = ob.get("title_hi") or ob["title"]
    detail_hi = f"{amount}, आख़िरी तारीख़ {hindi_date(due)}" if amount else f"आख़िरी तारीख़ {hindi_date(due)}"
    detail_en = f"{amount}, due {due:%d %b}" if amount else f"due {due:%d %b}"
    hi = f"पापा ने अभी तक {title_hi} ({detail_hi}) को 'हो गया' नहीं किया है। एक बार उनसे बात कर लीजिए।"
    en = f"Papa hasn't marked {ob['title']} ({detail_en}) as done. Please check with him."
    return hi, en
