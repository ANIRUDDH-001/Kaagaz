"""Acceptance test 1: a reminder fires from Temporal Cloud even while Render sleeps.

  python -m scripts.infra_proof start --minutes 20    # starts the workflow, prints the obligation id
  python -m scripts.infra_proof check <obligation_id> # shows whether the reminder reached the inbox
"""
import argparse
import asyncio
from datetime import timedelta

from app.clock import now_utc, today_ist
from app.config import get_settings
from app.db import connect_store, new_id
from flows.obligation_workflow import ObligationArgs, ObligationWorkflow
from flows.temporal import TASK_QUEUE, connect_temporal


async def start(minutes: int) -> None:
    s = get_settings()
    store = connect_store(s)
    await store.ensure_indexes()
    client = await connect_temporal(s)
    now = now_utc()
    _, hh = await store.create_household("demo", now)
    oid = new_id()
    due = (today_ist(now) + timedelta(days=30)).isoformat()
    await store.insert_obligation({"_id": oid, "household_id": hh["_id"], "title": "Infrastructure proof",
                                   "title_hi": "जाँच", "amount_inr": None, "due_date": due, "status": "active",
                                   "remind_offsets_days": [1], "escalate": False, "history": [],
                                   "created_at": now, "expires_at": hh["expires_at"]})
    await client.start_workflow(ObligationWorkflow.run,
                                ObligationArgs(oid, hh["_id"], due, [1], "demo", False, minutes * 60),
                                id=f"obligation-{oid}", task_queue=TASK_QUEUE)
    print(f"started obligation {oid}; reminder due at {now + timedelta(minutes=minutes):%H:%M} UTC")
    print(f"check later with: python -m scripts.infra_proof check {oid}")


async def check(oid: str) -> None:
    store = connect_store(get_settings())
    docs = await store.db.notifications.find({"obligation_id": oid}).to_list(None)
    if not docs:
        print("no notification yet")
    for d in docs:
        print(f"{d['_id']}: created {d['created_at']:%H:%M:%S} UTC, push_sent_at={d.get('push_sent_at')}")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("start")
    st.add_argument("--minutes", type=int, default=20)
    ck = sub.add_parser("check")
    ck.add_argument("obligation_id")
    a = p.parse_args()
    asyncio.run(start(a.minutes) if a.cmd == "start" else check(a.obligation_id))


if __name__ == "__main__":
    main()
