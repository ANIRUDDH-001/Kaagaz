"""Prompts and JSON schemas. Same text for hosted and local Gemma."""
import json

CATEGORIES = ["motor_insurance", "health_insurance", "life_insurance", "electricity_bill", "water_bill",
              "gas_bill", "school_fee", "college_fee", "property_tax", "certificate_renewal", "other"]
TOOLS = ["create_obligation", "update_obligation", "mark_done", "snooze", "answer", "clarify"]

_S = {"type": ["string", "null"]}
_N = {"type": ["number", "null"]}

PAPER_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "issuer": {"type": "string"},
        "title": {"type": "string"},
        "title_hi": {"type": "string"},
        "amount_inr": _N,
        "due_date": _S,
        "action": {"type": "string"},
        "consequence": _S,
        "evidence_amount": _S,
        "evidence_due_date": _S,
        "evidence_consequence": _S,
        "summary_hi": {"type": "string"},
    },
    "required": ["category", "issuer", "title", "title_hi", "amount_inr", "due_date", "action", "consequence",
                 "evidence_amount", "evidence_due_date", "evidence_consequence", "summary_hi"],
}

_PLAN_FIELDS = {
    "obligation_id": _S, "title": _S, "title_hi": _S, "category": _S, "amount_inr": _N, "due_date": _S,
    "action": _S, "consequence": _S, "evidence": _S, "remind_before_days": {"type": ["integer", "null"]},
    "escalate": {"type": ["boolean", "null"]}, "until": _S, "text_hi": _S, "question_hi": _S,
}
_TOOL_FIELDS = {
    "create_obligation": ["title", "title_hi", "category", "amount_inr", "due_date", "action", "consequence",
                          "evidence", "remind_before_days", "escalate"],
    "update_obligation": ["obligation_id", "amount_inr", "due_date"],
    "mark_done": ["obligation_id"],
    "snooze": ["obligation_id", "until"],
    "answer": ["obligation_id", "text_hi"],
    "clarify": ["question_hi"],
}


def _branch(tool: str) -> dict:
    # Every field a tool declares is required (nullable): Ollama lets a small model skip optional ones.
    props = {"tool": {"type": "string", "enum": [tool]}, **{f: _PLAN_FIELDS[f] for f in _TOOL_FIELDS[tool]}}
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


PLAN_SCHEMA = {
    "type": "object",
    "properties": {"actions": {"type": "array", "items": {"anyOf": [_branch(t) for t in TOOLS]}}},
    "required": ["actions"],
}


def paper_prompt(today_label: str) -> str:
    return f"""You help an Indian father manage important household papers. Today is {today_label}.
Read this photo of a paper and extract what he must do.
Rules:
- Copy facts only from the paper. If the paper does not show something, use null. Never guess.
- amount_inr: the total amount printed on the paper that must be paid by the last date, as a plain number.
  Copy it exactly as printed. Never calculate discounts, rebates, fines or interest yourself.
- due_date: the last date to act, as YYYY-MM-DD.
- evidence_amount, evidence_due_date, evidence_consequence: the exact words on the paper that show each value.
- consequence: what happens if he misses the date, only if the paper says so; otherwise null.
- category: one of {CATEGORIES}.
- title: a short English name, e.g. "Car insurance renewal". title_hi: the same in simple Hindi (Devanagari).
- action: what he must do, in short English.
- summary_hi: 2 simple sentences in Hindi (Devanagari) for an elderly reader."""


def plan_prompt(today_label: str, items: list[dict], said: str) -> str:
    return f"""You are the agent behind Kaagaz, a voice app for an Indian father who manages household papers.
Today is {today_label}. He speaks Hindi, Hinglish or English. Turn what he said into actions, using only these tools:
- create_obligation: something new to pay or do by a date. Fill title (short English), title_hi (Hindi),
  category (one of {CATEGORIES}), amount_inr, due_date, action, evidence (his exact words for the amount and date),
  remind_before_days if he asks to be reminded N days before, escalate true if he says to tell his son.
- update_obligation: change the amount or the date of an existing item (obligation_id from the list below).
- mark_done: he says an existing item is done or paid (obligation_id).
- snooze: he asks to be reminded later about an existing item (obligation_id, until as YYYY-MM-DD).
- answer: he asks a question. Answer in text_hi (simple Hindi, Devanagari) using ONLY the items below.
  If they don't contain the answer, say so. Put the id of the item you used in obligation_id.
- clarify: you can't tell what he means, or which item he means. Ask in question_hi (Hindi).
Dates: resolve words like "Friday" or "chaudah December" relative to today and pick the next future date.
Amounts: plain rupee numbers. Never invent an amount or a date he didn't say.
His current items (JSON): {json.dumps(items, ensure_ascii=False, default=str)}
He said: {said}"""
