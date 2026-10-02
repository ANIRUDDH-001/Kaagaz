"""Hindi voice via ElevenLabs, cached in MongoDB so repeated readbacks cost no credits.
In private mode (TTS_BACKEND=browser) the browser speaks instead and nothing leaves the device."""
import hashlib
import re

import httpx

from app.clock import now_utc

API = "https://api.elevenlabs.io"
RUPEES = re.compile(r"₹\s?(\d+(?:,\d+)*)")


def speakable(text: str, lang: str) -> str:
    """Voices read "₹2,346" as the letters "R S"; say the amount as a number of rupees instead."""
    if lang == "hi":
        return RUPEES.sub(lambda m: f"{m.group(1).replace(',', '')} रुपये", text)
    return RUPEES.sub(lambda m: f"{m.group(1)} rupees", text)


class ElevenLabsTTS:
    def __init__(self, api_key: str, model: str, voice_id: str, store,
                 transport: httpx.AsyncBaseTransport | None = None):
        self.api_key = api_key
        self.model = model
        self.voice_id = voice_id
        self.store = store
        self.transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=60, transport=self.transport, headers={"xi-api-key": self.api_key})

    async def _voice(self) -> str:
        if not self.voice_id:
            async with self._client() as client:
                r = await client.get(f"{API}/v2/voices", params={"page_size": 1})
            r.raise_for_status()
            self.voice_id = r.json()["voices"][0]["voice_id"]
        return self.voice_id

    async def synthesize(self, text: str, lang: str = "hi") -> bytes:
        voice = await self._voice()
        key = hashlib.sha256(f"{voice}|{self.model}|{lang}|{text}".encode()).hexdigest()
        cached = await self.store.tts_get(key)
        if cached:
            return cached
        body = {"text": speakable(text, lang), "model_id": self.model}
        if "flash" in self.model or "turbo" in self.model:
            body["language_code"] = lang
        async with self._client() as client:
            r = await client.post(f"{API}/v1/text-to-speech/{voice}", json=body,
                                  params={"output_format": "mp3_44100_64"})
        r.raise_for_status()
        await self.store.tts_put(key, r.content, now_utc())
        return r.content


def make_tts(settings, store) -> ElevenLabsTTS | None:
    if settings.tts_backend == "browser":
        return None
    return ElevenLabsTTS(settings.elevenlabs_api_key, settings.elevenlabs_tts_model,
                         settings.elevenlabs_voice_id, store)
