import json

import httpx
import pytest

from ai.errors import BadInput
from ai.stt import ElevenLabsSTT
from ai.tts import ElevenLabsTTS, make_tts
from app.config import get_settings
from tests.fakes import mock_store


async def test_scribe_request_and_text(tmp_path):
    clip = tmp_path / "a.webm"
    clip.write_bytes(b"audio")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers["xi-api-key"]
        seen["body"] = request.content
        return httpx.Response(200, json={"text": "  बिजली का बिल  "})

    stt = ElevenLabsSTT("k", transport=httpx.MockTransport(handler))
    assert await stt.transcribe(str(clip), "audio/webm") == "बिजली का बिल"
    assert seen["url"] == "https://api.elevenlabs.io/v1/speech-to-text" and seen["key"] == "k"
    assert b"scribe_v2" in seen["body"]


async def test_scribe_rejects_bad_audio(tmp_path):
    clip = tmp_path / "a.webm"
    clip.write_bytes(b"x")
    stt = ElevenLabsSTT("k", transport=httpx.MockTransport(lambda r: httpx.Response(422, text="bad audio")))
    with pytest.raises(BadInput):
        await stt.transcribe(str(clip), "audio/webm")


async def test_tts_picks_a_voice_and_caches():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.path == "/v2/voices":
            return httpx.Response(200, json={"voices": [{"voice_id": "v1"}]})
        return httpx.Response(200, content=b"MP3")

    tts = ElevenLabsTTS("k", "eleven_flash_v2_5", "", mock_store(), transport=httpx.MockTransport(handler))
    assert await tts.synthesize("नमस्ते") == b"MP3"
    assert await tts.synthesize("नमस्ते") == b"MP3"
    assert len([c for c in calls if "/text-to-speech/v1" in c]) == 1


def test_browser_tts_means_no_server_voice(monkeypatch):
    monkeypatch.setenv("TTS_BACKEND", "browser")
    get_settings.cache_clear()
    assert make_tts(get_settings(), mock_store()) is None


async def test_tts_sends_the_language_and_caches_per_language():
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, content=b"MP3")

    tts = ElevenLabsTTS("k", "eleven_flash_v2_5", "v1", mock_store(), transport=httpx.MockTransport(handler))
    await tts.synthesize("10 October", lang="en")
    await tts.synthesize("10 October", lang="hi")
    await tts.synthesize("10 October", lang="en")    # cached
    assert [b["language_code"] for b in bodies] == ["en", "hi"]


def test_rupee_amounts_are_said_as_words_not_letters():
    from ai.tts import speakable
    assert speakable("बिजली का बिल, ₹2,346 — आख़िरी तारीख़ 10 अक्टूबर।", "hi") == \
        "बिजली का बिल, 2346 रुपये — आख़िरी तारीख़ 10 अक्टूबर।"
    assert speakable("Car insurance, ₹18,400, due 14 Dec.", "en") == "Car insurance, 18,400 rupees, due 14 Dec."
    assert speakable("₹ 1,50,000 aur ₹500", "hi") == "150000 रुपये aur 500 रुपये"


async def test_tts_sends_speakable_text():
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, content=b"MP3")

    tts = ElevenLabsTTS("k", "eleven_multilingual_v2", "v1", mock_store(), transport=httpx.MockTransport(handler))
    await tts.synthesize("₹2,346 सही है?", lang="hi")
    assert bodies[0]["text"] == "2346 रुपये सही है?"
