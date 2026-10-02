"""Turn Gemma's output into a confirmation card. Everything the model says is validated here;
nothing reaches the database until the user confirms the card."""
import math
import re
from datetime import date, timedelta

from ai.prompts import CATEGORIES, PAPER_SCHEMA, PLAN_SCHEMA, paper_prompt, plan_prompt
from app.clock import hindi_date, today_label
from flows.messages import inr

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
MONTH_WORDS = {
    1: ("jan", "जनवरी"), 2: ("feb", "फ़रवरी", "फरवरी"), 3: ("mar", "मार्च"), 4: ("apr", "अप्रैल"),
    5: ("may", "मई"), 6: ("jun", "जून"), 7: ("jul", "जुलाई"), 8: ("aug", "अगस्त"),
    9: ("sep", "सितंबर", "सितम्बर"), 10: ("oct", "अक्टूबर", "अक्तूबर"), 11: ("nov", "नवंबर", "नवम्बर"),
    12: ("dec", "दिसंबर", "दिसम्बर"),
}
NEEDS_ID = {"update_obligation", "mark_done", "snooze"}
DEFAULT_OFFSETS = [30, 7, 1]
NOT_UNDERSTOOD = "माफ़ कीजिए, समझ नहीं पाया। फिर से बोलिए।"


def _float(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _date(v) -> date | None:
    try:
        return date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def _clarify(question: str) -> dict:
    return {"tool": "clarify", "question_hi": question}


def amount_supported(amount: float, evidence: str | None) -> bool:
    digits = re.sub(r"\D", "", (evidence or "").translate(DEVANAGARI_DIGITS))
    return str(int(round(amount))) in digits


def date_supported(d: date, evidence: str | None) -> bool:
    text = (evidence or "").translate(DEVANAGARI_DIGITS)
    small = [int(n) for n in re.findall(r"\d+", text) if len(n) <= 2]
    lower = text.lower()
    day_ok = d.day in small
    month_ok = d.month in small or any(w in lower for w in MONTH_WORDS[d.month])
    years = {int(n) for n in re.findall(r"(?<!\d)(\d{4})(?!\d)", text) if 1990 <= int(n) <= 2100}
    year_ok = not years or d.year in years   # a printed year must match; none printed is fine
    return day_ok and month_ok and year_ok


def _offsets(a: dict) -> list[int]:
    given = a.get("remind_offsets_days")
    if isinstance(given, list) and given and all(isinstance(o, int) and 1 <= o <= 60 for o in given):
        return sorted(set(given), reverse=True)
    rb = a.get("remind_before_days")
    if isinstance(rb, (int, float)) and 1 <= rb <= 60:
        return sorted({int(rb), 1}, reverse=True)
    return list(DEFAULT_OFFSETS)


def validate_create(a: dict, today: date, source: str) -> dict:
    needs: list[str] = []
    check_evidence = source == "photo"

    amount = _float(a.get("amount_inr"))
    if amount is not None and not 0 < amount < 1e7:
        amount = None
        needs.append("amount_inr")
    ev_amount = a.get("evidence_amount") or a.get("evidence")
    if check_evidence and amount is not None and not amount_supported(amount, ev_amount):
        needs.append("amount_inr")

    due = _date(a.get("due_date"))
    if due is not None and not today - timedelta(days=60) <= due <= today + timedelta(days=730):
        due = None
    ev_due = a.get("evidence_due_date") or a.get("evidence")
    if due is None:
        needs.append("due_date")
    elif check_evidence and not date_supported(due, ev_due):
        needs.append("due_date")

    consequence = a.get("consequence") or None
    ev_consequence = a.get("evidence_consequence")
    if check_evidence and consequence and not ev_consequence:
        consequence = None

    category = a.get("category") if a.get("category") in CATEGORIES else "other"
    return {
        "tool": "create_obligation",
        "source": a.get("source", "photo") if source == "confirm" else source,
        "title": (a.get("title") or "").strip()[:80] or "Important paper",
        "title_hi": (a.get("title_hi") or "").strip()[:80] or None,
        "category": category,
        "amount_inr": amount,
        "due_date": due.isoformat() if due else None,
        "action": (a.get("action") or "").strip()[:200],
        "consequence": consequence,
        "evidence_amount": ev_amount,
        "evidence_due_date": ev_due,
        "evidence_consequence": ev_consequence,
        "summary_hi": a.get("summary_hi"),
        "remind_offsets_days": _offsets(a),
        # The son is told by default; only an explicit untick on the card turns it off.
        "escalate": not (source == "confirm" and a.get("escalate") is False),
        "needs_check": sorted(set(needs)),
    }


def validate_plan(actions: list[dict], obligations_by_id: dict[str, dict], today: date, source: str) -> list[dict]:
    out: list[dict] = []
    for a in actions:
        tool = a.get("tool")
        if tool == "create_obligation":
            out.append(validate_create(a, today, source))
        elif tool in NEEDS_ID:
            ob = obligations_by_id.get(a.get("obligation_id") or "")
            if ob is None:
                out.append(_clarify("कौन से काग़ज़ की बात है? उसका नाम बताइए।"))
                continue
            item = {"tool": tool, "obligation_id": ob["_id"], "title": ob.get("title"), "title_hi": ob.get("title_hi")}
            if tool == "snooze":
                until = _date(a.get("until"))
                if until is None or until < today:
                    out.append(_clarify("किस तारीख़ को फिर याद दिलाऊँ?"))
                    continue
                item["until"] = until.isoformat()
            if tool == "update_obligation":
                amount = _float(a.get("amount_inr"))
                due = _date(a.get("due_date"))
                amount = amount if amount is not None and 0 < amount < 1e7 else None
                if amount is None and due is None:
                    out.append(_clarify("क्या बदलना है — रकम या तारीख़?"))
                    continue
                item["amount_inr"] = amount
                item["due_date"] = due.isoformat() if due else None
            out.append(item)
        elif tool == "answer" and a.get("text_hi"):
            used = [a["obligation_id"]] if a.get("obligation_id") in obligations_by_id else []
            out.append({"tool": "answer", "text_hi": a["text_hi"].strip()[:600], "used_obligation_ids": used})
        elif tool == "clarify":
            out.append(_clarify((a.get("question_hi") or NOT_UNDERSTOOD).strip()[:300]))
    return out


def readback(actions: list[dict]) -> str:
    parts: list[str] = []
    changes = no_date = False
    for a in actions:
        tool = a["tool"]
        name = a.get("title_hi") or a.get("title") or "काग़ज़"
        if tool == "create_obligation":
            changes = True
            s = name
            if a.get("amount_inr"):
                s += f", {inr(a['amount_inr'])}"
            if a.get("due_date"):
                s += f", आख़िरी तारीख़ {hindi_date(date.fromisoformat(a['due_date']))}"
            else:
                no_date = True
            parts.append(s + "।")
        elif tool == "mark_done":
            changes = True
            parts.append(f"{name} — हो गया।")
        elif tool == "snooze":
            changes = True
            parts.append(f"{name} — {hindi_date(date.fromisoformat(a['until']))} को फिर याद दिलाऊँगा।")
        elif tool == "update_obligation":
            changes = True
            bits = []
            if a.get("amount_inr"):
                bits.append(f"नई रकम {inr(a['amount_inr'])}")
            if a.get("due_date"):
                bits.append(f"नई तारीख़ {hindi_date(date.fromisoformat(a['due_date']))}")
            parts.append(f"{name} — {', '.join(bits)}।")
        elif tool == "answer":
            parts.append(a["text_hi"])
        elif tool == "clarify":
            parts.append(a["question_hi"])
    text = " ".join(parts)
    if no_date:   # hard rule 1: never guess a date; ask for it
        return f"{text} तारीख़ नहीं मिली — काग़ज़ पर देखकर बताइए।"
    return f"{text} सही है?" if changes else text


async def read_paper(gemma, image: bytes, mime: str, today: date) -> dict:
    raw = await gemma.generate_json(paper_prompt(today_label(today)), PAPER_SCHEMA, image=image, mime=mime)
    action = validate_create(raw, today, source="photo")
    return {"kind": "paper", "transcript": None, "summary_hi": raw.get("summary_hi"),
            "actions": [action], "readback_hi": readback([action])}


async def plan_speech(gemma, said: str, obligations: list[dict], today: date, source: str = "voice") -> dict:
    said = (said or "").strip()
    items = [{"id": o["_id"], "title": o.get("title"), "title_hi": o.get("title_hi"),
              "amount_inr": o.get("amount_inr"), "due_date": o.get("due_date"), "status": o.get("status")}
             for o in obligations][:50]
    raw = await gemma.generate_json(plan_prompt(today_label(today), items, said), PLAN_SCHEMA)
    actions = validate_plan(raw.get("actions") or [], {o["_id"]: o for o in obligations}, today, source)
    if not actions:
        actions = [_clarify(NOT_UNDERSTOOD)]
    return {"kind": "speech", "transcript": said, "summary_hi": None, "actions": actions,
            "readback_hi": readback(actions)}
