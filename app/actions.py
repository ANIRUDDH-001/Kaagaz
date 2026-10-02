"""Run confirmed actions. The only code path that changes obligations or starts workflows."""
from datetime import date, datetime, timedelta

from pymongo.errors import DuplicateKeyError
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.service import RPCError, RPCStatusCode

from ai.understand import validate_create
from app.clock import today_ist
from app.i18n import msg
from flows.obligation_workflow import ObligationArgs, ObligationWorkflow
from flows.temporal import TASK_QUEUE

STORED_FIELDS = ("title", "title_hi", "category", "amount_inr", "due_date", "action", "consequence",
                 "evidence_amount", "evidence_due_date", "evidence_consequence", "summary_hi",
                 "remind_offsets_days", "escalate", "source", "scam")
CHANGES = ("create_obligation", "mark_done", "snooze", "update_obligation")
YEARLY = {"motor_insurance", "health_insurance", "life_insurance", "property_tax", "certificate_renewal"}
# What the confirmation card lets the user edit. Everything else comes from the card the server made.
EDITABLE = {"create_obligation": ("title", "title_hi", "amount_inr", "due_date", "action", "escalate",
                                  "remind_offsets_days")}


class ActionError(Exception):
    """A confirmed action can't be carried out. `message` is shown to the user in their language."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code
        self.message = msg(code)


def bind_to_card(card_actions: list[dict], submitted: list[dict]) -> list[dict]:
    """Confirm means "yes to this card". The browser may change only the fields the card shows as
    editable; it can't add, drop, swap or retarget an action that Gemma didn't propose."""
    proposed = [a for a in card_actions if a.get("tool") in CHANGES]
    if len(submitted) != len(proposed):
        raise ActionError("card_changed")
    bound = []
    for want, got in zip(proposed, submitted):
        if got.get("tool") != want["tool"] or got.get("obligation_id") != want.get("obligation_id"):
            raise ActionError("card_changed")
        bound.append({**want, **{k: got[k] for k in EDITABLE.get(want["tool"], ()) if k in got}})
    return bound


async def _signal(temporal, workflow_id: str, signal, *args, needs_workflow: bool = False) -> None:
    """`needs_workflow`: the change only means something if reminders follow (snooze, new date), so it is sent
    before the database write and a closed workflow is an error. Done and cancel stand on the database alone."""
    try:
        await temporal.get_workflow_handle(workflow_id).signal(signal, *args)
    except RPCError as e:
        if not needs_workflow:
            return   # reminders check the database before sending
        if e.status == RPCStatusCode.NOT_FOUND:
            raise ActionError("reminders_closed") from None
        raise ActionError("try_later") from None


def _event(now: datetime, role: str, event: str, detail=None) -> dict:
    return {"at": now, "by_role": role, "event": event, "detail": detail}


def next_year_due(due: date, today: date) -> date:
    """The same day a year on, or the first such day that hasn't passed. Feb 29 becomes Feb 28."""
    years = 1
    while True:
        year = due.year + years
        d = date(year, 2, 28) if (due.month, due.day) == (2, 29) else due.replace(year=year)
        if d >= today:
            return d
        years += 1


def repeat_offer(ob: dict, today: date) -> dict | None:
    if ob.get("category") not in YEARLY:
        return None
    return {"obligation_id": ob["_id"],
            "due_date": next_year_due(date.fromisoformat(ob["due_date"]), today).isoformat()}


async def _start(temporal, hh: dict, oid: str, due: str, offsets: list[int], escalate: bool) -> None:
    args = ObligationArgs(oid, hh["_id"], due, offsets, "demo" if hh["mode"] == "demo" else "real", escalate)
    try:
        await temporal.start_workflow(ObligationWorkflow.run, args, id=f"obligation-{oid}", task_queue=TASK_QUEUE,
                                      id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE)
    except WorkflowAlreadyStartedError:
        pass


async def create_obligation(store, temporal, hh: dict, a: dict, role: str, now: datetime,
                            oid: str, input_id: str) -> dict:
    """`oid` is derived from the input, so a retried confirm finds its own record instead of adding one."""
    v = validate_create(a, today_ist(now), source="confirm")
    if not v["due_date"]:
        raise ActionError("date_required")
    doc = {"_id": oid, "household_id": hh["_id"], **{k: v[k] for k in STORED_FIELDS},
           "status": "active", "snoozed_until": None, "snoozed_at": None, "workflow_id": f"obligation-{oid}",
           "source_input_id": input_id, "history": [_event(now, role, "created")], "created_at": now,
           "expires_at": hh.get("expires_at")}
    try:
        await store.insert_obligation(doc)
    except DuplicateKeyError:
        pass   # a retry after a crash: the record exists; make sure its workflow does too
    await _start(temporal, hh, oid, v["due_date"], v["remind_offsets_days"], v["escalate"])
    return {"tool": "create_obligation", "ok": True, "obligation_id": oid}


async def mark_done(store, temporal, ob: dict, role: str, now: datetime) -> dict | None:
    """Returns next year's offer for a paper that comes every year (the UI asks; nothing is added here)."""
    offer = repeat_offer(ob, today_ist(now))
    if ob["status"] == "done":
        return offer
    await store.set_obligation(ob["_id"], {"status": "done", "done_at": now}, _event(now, role, "done"))
    await _signal(temporal, ob["workflow_id"], ObligationWorkflow.mark_done)
    return offer


async def repeat_obligation(store, temporal, hh: dict, ob: dict, role: str, now: datetime) -> dict:
    """Next year's reminder for a renewal. The tap on "Yes" is the confirmation. Next year's amount isn't known,
    so it stays empty (last year's is kept to show); the id comes from the old one, so a double tap adds one."""
    if ob.get("category") not in YEARLY:
        raise ActionError("not_yearly")
    if ob["status"] != "done":
        raise ActionError("not_done_yet")
    due = next_year_due(date.fromisoformat(ob["due_date"]), today_ist(now)).isoformat()
    oid = f"{ob['_id']}-y{due[:4]}"
    doc = {"_id": oid, "household_id": hh["_id"], **{k: ob.get(k) for k in STORED_FIELDS},
           "amount_inr": None, "last_amount_inr": ob.get("amount_inr"), "due_date": due,
           "evidence_amount": None, "evidence_due_date": None, "evidence_consequence": None, "scam": None,
           "source": "repeat", "repeat_of": ob["_id"], "status": "active", "snoozed_until": None,
           "snoozed_at": None, "workflow_id": f"obligation-{oid}", "source_input_id": None,
           "history": [_event(now, role, "created", {"repeat_of": ob["_id"]})], "created_at": now,
           "expires_at": hh.get("expires_at")}
    try:
        await store.insert_obligation(doc)
    except DuplicateKeyError:
        pass
    await _start(temporal, hh, oid, due, ob.get("remind_offsets_days") or [30, 7, 1], ob.get("escalate", True))
    return {"ok": True, "obligation_id": oid, "due_date": due}


async def snooze(store, temporal, ob: dict, until: str, role: str, now: datetime) -> None:
    try:
        d = date.fromisoformat(until)
    except (TypeError, ValueError):
        raise ActionError("date_unclear") from None
    if d < today_ist(now):
        raise ActionError("date_past")
    if ob["status"] != "active":
        raise ActionError("already_done")
    await _signal(temporal, ob["workflow_id"], ObligationWorkflow.snooze, d.isoformat(), needs_workflow=True)
    await store.set_obligation(ob["_id"], {"snoozed_until": d.isoformat(), "snoozed_at": now},
                               _event(now, role, "snooze", d.isoformat()))


async def update_obligation(store, temporal, ob: dict, a: dict, role: str, now: datetime) -> None:
    fields = {}
    if a.get("amount_inr") is not None:
        amount = float(a["amount_inr"])
        if not 0 < amount < 1e7:
            raise ActionError("amount_wrong")
        fields["amount_inr"] = amount
    if a.get("due_date"):
        try:
            due = date.fromisoformat(a["due_date"])
        except ValueError:
            raise ActionError("date_unclear") from None
        today = today_ist(now)
        if not today - timedelta(days=60) <= due <= today + timedelta(days=730):   # same window as create
            raise ActionError("date_wrong")
        fields["due_date"] = due.isoformat()
    if not fields:
        raise ActionError("nothing_changed")
    if fields.get("due_date") and fields["due_date"] != ob["due_date"]:
        await _signal(temporal, ob["workflow_id"], ObligationWorkflow.update_due, fields["due_date"],
                      needs_workflow=True)
        fields["due_changed_at"] = now
    await store.set_obligation(ob["_id"], fields, _event(now, role, "update", fields))


async def execute_actions(store, temporal, hh: dict, actions: list[dict], role: str, now: datetime,
                          input_id: str) -> list[dict]:
    results = []
    for n, a in enumerate(actions):
        tool = a.get("tool")
        if tool == "create_obligation":
            results.append(await create_obligation(store, temporal, hh, a, role, now, f"{input_id}-{n}", input_id))
        elif tool in ("mark_done", "snooze", "update_obligation"):
            ob = await store.get_obligation(a.get("obligation_id") or "", hh["_id"])
            if ob is None:
                raise ActionError("not_found")
            if tool == "mark_done":
                offer = await mark_done(store, temporal, ob, role, now)
                results.append({"tool": tool, "ok": True, "obligation_id": ob["_id"], "repeat_offer": offer})
                continue
            if tool == "snooze":
                await snooze(store, temporal, ob, a.get("until") or "", role, now)
            else:
                await update_obligation(store, temporal, ob, a, role, now)
            results.append({"tool": tool, "ok": True, "obligation_id": ob["_id"]})
        else:
            results.append({"tool": tool, "ok": True})
    return results
