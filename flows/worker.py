"""Reminder worker. Runs inside the API process, and as a short-lived job on GitHub Actions:
python -m flows.worker --drain-seconds 180"""
import argparse
import asyncio
import logging
from datetime import timedelta

from temporalio.worker import Worker

from app.config import get_settings
from app.db import connect_store
from flows.activities import ReminderActivities
from flows.ai_activities import AIActivities
from flows.obligation_workflow import ObligationWorkflow
from flows.process_workflow import ProcessInputWorkflow
from flows.push import WebPushSender
from flows.temporal import TASK_QUEUE, ai_task_queue, connect_temporal


def reminder_worker(client, store, push) -> Worker:
    acts = ReminderActivities(store, push)
    return Worker(client, task_queue=TASK_QUEUE, workflows=[ObligationWorkflow],
                  activities=[acts.send_reminder, acts.send_escalation],
                  graceful_shutdown_timeout=timedelta(seconds=30))


def ai_worker(client, acts: AIActivities) -> Worker:
    return Worker(client, task_queue=ai_task_queue(), workflows=[ProcessInputWorkflow],
                  activities=[acts.transcribe, acts.understand, acts.fail],
                  graceful_shutdown_timeout=timedelta(seconds=30))


async def run_for(workers: list[Worker], seconds: float | None) -> None:
    tasks = [asyncio.create_task(w.run()) for w in workers]
    if seconds is None:
        await asyncio.gather(*tasks)
        return
    await asyncio.sleep(seconds)
    await asyncio.gather(*(w.shutdown() for w in workers))
    await asyncio.gather(*tasks, return_exceptions=True)


async def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--drain-seconds", type=float, default=None,
                        help="poll for this long, then exit (GitHub Actions); default: run forever")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    store = connect_store(settings)
    await store.ensure_indexes()
    client = await connect_temporal(settings)
    push = WebPushSender(settings.vapid_private_key, settings.vapid_subject)
    await run_for([reminder_worker(client, store, push)], args.drain_seconds)


if __name__ == "__main__":
    asyncio.run(main())
