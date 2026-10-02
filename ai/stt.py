"""Speech-to-text: ElevenLabs Scribe (public demo) or Whisper on this machine (private mode)."""
import asyncio
import os

import httpx

from ai.errors import BadInput


class ElevenLabsSTT:
    name = "elevenlabs:scribe_v2"

    def __init__(self, api_key: str, transport: httpx.AsyncBaseTransport | None = None):
        self.api_key = api_key
        self.transport = transport

    async def transcribe(self, path: str, mime: str) -> str:
        with open(path, "rb") as f:
            data = f.read()
        async with httpx.AsyncClient(timeout=120, transport=self.transport) as client:
            r = await client.post("https://api.elevenlabs.io/v1/speech-to-text",
                                  headers={"xi-api-key": self.api_key}, data={"model_id": "scribe_v2"},
                                  files={"file": (os.path.basename(path), data, mime)})
        if r.status_code in (400, 422):
            raise BadInput(r.text[:300])
        r.raise_for_status()
        return (r.json().get("text") or "").strip()


class WhisperSTT:
    """faster-whisper large-v3-turbo on CPU. Forced to Hindi: auto-detect wrote Hinglish in Urdu script."""
    name = "whisper:large-v3-turbo"
    _model = None

    async def transcribe(self, path: str, mime: str) -> str:
        def run() -> str:
            from faster_whisper import WhisperModel

            if WhisperSTT._model is None:
                WhisperSTT._model = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
            segments, _ = WhisperSTT._model.transcribe(path, language="hi", beam_size=5, vad_filter=True)
            return " ".join(s.text.strip() for s in segments).strip()

        return await asyncio.to_thread(run)


def make_stt(settings):
    if settings.stt_backend == "whisper":
        return WhisperSTT()
    return ElevenLabsSTT(settings.elevenlabs_api_key)
