import base64
import json

import httpx
import pytest

from ai.errors import BadInput
from ai.gemma import GeminiGemma, OllamaGemma, make_gemma, parse_json
from app.config import get_settings


def test_parse_json_variants():
    assert parse_json('{"a": 1}') == {"a": 1}
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('Here you go: {"a": {"b": 2}} thanks') == {"a": {"b": 2}}
    with pytest.raises(json.JSONDecodeError):
        parse_json("no json here")


async def test_ollama_request_shape():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": '{"ok": true}'}})

    g = OllamaGemma("http://localhost:11434/", "gemma4:e4b", transport=httpx.MockTransport(handler))
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    assert await g.generate_json("read this", schema, image=b"img") == {"ok": True}
    body = seen["body"]
    assert seen["url"] == "http://localhost:11434/api/chat"
    assert body["model"] == "gemma4:e4b" and body["format"] == schema
    assert body["think"] is False and body["stream"] is False and body["options"]["temperature"] == 0
    assert body["messages"][0]["images"] == [base64.b64encode(b"img").decode()]


async def test_ollama_400_is_bad_input_and_500_is_retryable():
    bad = OllamaGemma("http://x", "m", transport=httpx.MockTransport(lambda r: httpx.Response(400, text="bad")))
    with pytest.raises(BadInput):
        await bad.generate_json("p", {})
    busy = OllamaGemma("http://x", "m", transport=httpx.MockTransport(lambda r: httpx.Response(500, text="x")))
    with pytest.raises(httpx.HTTPStatusError):
        await busy.generate_json("p", {})


def test_make_gemma_picks_backend(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    get_settings.cache_clear()
    assert isinstance(make_gemma(get_settings()), OllamaGemma)
    monkeypatch.setenv("LLM_BACKEND", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    g = make_gemma(get_settings())
    assert isinstance(g, GeminiGemma) and g.models == ["models/gemma-4-26b-a4b-it"]
