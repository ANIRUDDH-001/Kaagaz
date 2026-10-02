import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from ai.errors import BadInput
from app.inputs import InputStore
from flows.ai_activities import AIActivities
from flows.process_workflow import ProcessInputWorkflow
from tests.fakes import FakeGemma, FakeSTT, mock_store

Q = "test-ai"
PAPER = {"category": "electricity_bill", "issuer": "Discom", "title": "Electricity bill",
         "title_hi": "बिजली का बिल", "amount_inr": 2346, "due_date": "2026-10-10", "action": "Pay",
         "consequence": None, "evidence_amount": "Amount payable ₹2,346", "evidence_due_date": "Due date 10-10-2026",
         "evidence_consequence": None, "summary_hi": "बिजली का बिल।"}


@pytest.fixture
async def env():
    async with await WorkflowEnvironment.start_time_skipping() as e:
        yield e


async def run(env, inputs, gemma, stt, p):
    acts = AIActivities(inputs, mock_store(), gemma, stt)
    async with Worker(env.client, task_queue=Q, workflows=[ProcessInputWorkflow],
                      activities=[acts.transcribe, acts.understand, acts.fail]):
        return await env.client.execute_workflow(ProcessInputWorkflow.run, p.id, id=f"in-{p.id}", task_queue=Q)


async def test_photo_becomes_a_card_and_file_is_deleted(env, tmp_path):
    inputs = InputStore(str(tmp_path))
    p = inputs.create("h1", "parent", "photo", b"jpeg", "image/jpeg")
    assert await run(env, inputs, FakeGemma(PAPER), FakeSTT(""), p) == "ready"
    assert p.status == "ready" and p.card["actions"][0]["amount_inr"] == 2346
    assert p.path is None and list(tmp_path.iterdir()) == []


async def test_voice_is_transcribed_then_planned(env, tmp_path):
    inputs = InputStore(str(tmp_path))
    p = inputs.create("h1", "parent", "voice", b"webm", "audio/webm;codecs=opus")
    gemma = FakeGemma({"actions": [{"tool": "answer", "text_hi": "10 अक्टूबर तक।"}]})
    assert await run(env, inputs, gemma, FakeSTT("बिजली का बिल कब तक भरना है?"), p) == "ready"
    assert p.transcript == "बिजली का बिल कब तक भरना है?"
    assert p.card["readback_hi"] == "10 अक्टूबर तक।"


async def test_typed_text_skips_speech_to_text(env, tmp_path):
    inputs = InputStore(str(tmp_path))
    p = inputs.create("h1", "parent", "text", text="bijli ka bill kab hai")
    gemma = FakeGemma({"actions": [{"tool": "answer", "text_hi": "10 अक्टूबर।"}]})
    assert await run(env, inputs, gemma, FakeSTT("SHOULD NOT BE USED"), p) == "ready"
    assert p.transcript is None and "bijli ka bill kab hai" in gemma.calls[0]


async def test_silent_clip_fails_as_empty_without_calling_gemma(env, tmp_path):
    inputs = InputStore(str(tmp_path))
    p = inputs.create("h1", "parent", "voice", b"webm", "audio/webm")
    gemma = FakeGemma({"actions": []})
    assert await run(env, inputs, gemma, FakeSTT(""), p) == "failed"
    assert p.status == "failed" and p.error == "Empty" and gemma.calls == []


async def test_flaky_gemma_is_retried_then_reported_busy(env, tmp_path):
    inputs = InputStore(str(tmp_path))
    p = inputs.create("h1", "parent", "photo", b"jpeg", "image/jpeg")
    gemma = FakeGemma(RuntimeError("503 overloaded"))
    assert await run(env, inputs, gemma, FakeSTT(""), p) == "failed"
    assert p.error == "Busy" and len(gemma.calls) == 5


async def test_retry_succeeds_after_two_failures(env, tmp_path):
    inputs = InputStore(str(tmp_path))
    p = inputs.create("h1", "parent", "photo", b"jpeg", "image/jpeg")
    gemma = FakeGemma(RuntimeError("500"), RuntimeError("503"), PAPER)
    assert await run(env, inputs, gemma, FakeSTT(""), p) == "ready"
    assert len(gemma.calls) == 3


async def test_bad_input_is_not_retried(env, tmp_path):
    inputs = InputStore(str(tmp_path))
    p = inputs.create("h1", "parent", "photo", b"jpeg", "image/jpeg")
    gemma = FakeGemma(BadInput("unsupported image"))
    assert await run(env, inputs, gemma, FakeSTT(""), p) == "failed"
    assert p.error == "BadInput" and len(gemma.calls) == 1


async def test_upload_lost_after_restart_is_gone(env, tmp_path):
    inputs = InputStore(str(tmp_path))
    p = inputs.create("h1", "parent", "photo", b"jpeg", "image/jpeg")
    inputs.drop_file(p)
    assert await run(env, inputs, FakeGemma(PAPER), FakeSTT(""), p) == "failed"
    assert p.error == "Gone"
