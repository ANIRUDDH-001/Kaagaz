"""Test doubles shared by all tests."""
from mongomock_motor import AsyncMongoMockClient

from app.db import Store


def mock_store() -> Store:
    return Store(AsyncMongoMockClient(tz_aware=True)["kaagaz_test"])


class FakePush:
    name = "fake"

    def __init__(self, result: str = "ok"):
        self.calls: list[tuple[str, dict, str]] = []
        self.result = result

    async def send(self, subscription: dict, payload: dict, topic: str) -> str:
        self.calls.append((subscription["endpoint"], payload, topic))
        return self.result


class FakeGemma:
    """Returns the queued responses in order; the last one repeats. Exceptions are raised."""
    name = "fake"

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls: list[str] = []

    async def generate_json(self, prompt, schema, image=None, mime="image/jpeg"):
        self.calls.append(prompt)
        r = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(r, Exception):
            raise r
        return r


class FakeSTT:
    name = "fake"

    def __init__(self, text: str):
        self.text = text

    async def transcribe(self, path: str, mime: str) -> str:
        return self.text


class FakeHandle:
    def __init__(self, temporal: "FakeTemporal", workflow_id: str):
        self.temporal = temporal
        self.workflow_id = workflow_id

    async def signal(self, signal, *args):
        if self.temporal.signal_error is not None:
            raise self.temporal.signal_error
        self.temporal.signals.append((self.workflow_id, signal.__name__, args))


class FakeTemporal:
    def __init__(self):
        self.started: list[dict] = []
        self.signals: list[tuple] = []
        self.fail_next_start = False
        self.signal_error: Exception | None = None

    async def start_workflow(self, run_fn, arg, *, id: str, task_queue: str, execution_timeout=None,
                             id_reuse_policy=None):
        if self.fail_next_start:
            self.fail_next_start = False
            raise RuntimeError("temporal unreachable")
        if any(s["id"] == id for s in self.started):
            from temporalio.exceptions import WorkflowAlreadyStartedError
            raise WorkflowAlreadyStartedError(id, run_fn.__qualname__)
        self.started.append({"workflow": run_fn.__qualname__, "arg": arg, "id": id, "task_queue": task_queue,
                             "execution_timeout": execution_timeout})

    def get_workflow_handle(self, workflow_id: str) -> FakeHandle:
        return FakeHandle(self, workflow_id)
