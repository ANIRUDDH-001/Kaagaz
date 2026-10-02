"""Activities for understanding an upload. They run only in the process that received it
(see ai_task_queue), because the file is on that machine's disk."""
from dataclasses import dataclass
from pathlib import Path

from temporalio import activity
from temporalio.exceptions import ApplicationError

from ai.errors import BadInput
from ai.understand import plan_speech, read_paper
from app.clock import now_utc, today_ist


@dataclass
class FailArgs:
    input_id: str
    reason: str


def _stop(reason: str, message: str) -> ApplicationError:
    return ApplicationError(message, type=reason, non_retryable=True)


class AIActivities:
    def __init__(self, inputs, store, gemma, stt, clock=now_utc):
        self.inputs = inputs
        self.store = store
        self.gemma = gemma
        self.stt = stt
        self.clock = clock

    def _get(self, input_id: str):
        p = self.inputs.get(input_id)
        if p is None:
            raise _stop("Gone", "input no longer in memory")
        return p

    def _file(self, p) -> bytes:
        if not p.path or not Path(p.path).exists():
            raise _stop("Gone", "upload file missing")
        return Path(p.path).read_bytes()

    @activity.defn
    async def transcribe(self, input_id: str) -> None:
        p = self._get(input_id)
        if p.kind != "voice" or p.transcript:
            return
        self._file(p)
        try:
            text = await self.stt.transcribe(p.path, p.mime or "audio/webm")
        except BadInput as e:
            raise _stop("BadInput", str(e)) from e
        if not text.strip():
            raise _stop("Empty", "no speech heard")
        p.transcript = text.strip()

    @activity.defn
    async def understand(self, input_id: str) -> None:
        p = self._get(input_id)
        today = today_ist(self.clock())
        try:
            if p.kind == "photo":
                card = await read_paper(self.gemma, self._file(p), p.mime or "image/jpeg", today)
            else:
                said = p.transcript if p.kind == "voice" else p.text
                obligations = await self.store.list_obligations(p.household_id)
                card = await plan_speech(self.gemma, said, obligations, today, source=p.kind)
        except BadInput as e:
            raise _stop("BadInput", str(e)) from e
        p.card = card
        p.status = "ready"
        self.inputs.drop_file(p)

    @activity.defn
    async def fail(self, a: FailArgs) -> None:
        p = self.inputs.get(a.input_id)
        if p is None:
            return
        p.status = "failed"
        p.error = a.reason
        self.inputs.drop_file(p)
