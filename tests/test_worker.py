import time

from temporalio.testing import WorkflowEnvironment

from flows.temporal import TASK_QUEUE, ai_task_queue
from flows.worker import reminder_worker, run_for
from tests.fakes import FakePush, mock_store


def test_queue_names():
    assert TASK_QUEUE == "kaagaz"
    assert ai_task_queue().startswith("kaagaz-ai-")
    assert ai_task_queue() == ai_task_queue()   # stable within one process


async def test_drain_mode_stops_after_the_given_seconds():
    async with await WorkflowEnvironment.start_local() as env:
        w = reminder_worker(env.client, mock_store(), FakePush())
        t0 = time.monotonic()
        await run_for([w], 2)
        assert 1.5 < time.monotonic() - t0 < 40
