"""Gemma 4 behind one interface: hosted (Gemini API) for the public demo, Ollama for private mode."""
import base64
import json
import re
from typing import Protocol

import httpx

from ai.errors import BadInput


class Gemma(Protocol):
    name: str

    async def generate_json(self, prompt: str, schema: dict, image: bytes | None = None,
                            mime: str = "image/jpeg") -> dict: ...


def parse_json(text: str) -> dict:
    text = (text or "").strip()
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0) if m else text)


class GeminiGemma:
    """Hosted Gemma. thinking_level="minimal": 4-15 s per call instead of 18-36 s (measured 2026-10-02)."""

    def __init__(self, api_key: str, model: str, fallback: str = ""):
        from google import genai
        from google.genai import types

        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=180_000))
        self.models = [m for m in (model, fallback) if m]
        self.name = f"gemini:{model}"

    async def generate_json(self, prompt, schema, image=None, mime="image/jpeg"):
        from google.genai import errors, types

        parts = [types.Part.from_bytes(data=image, mime_type=mime)] if image else []
        parts.append(f"{prompt}\n\nReturn ONLY a JSON object matching this JSON schema:\n{json.dumps(schema)}")
        config = types.GenerateContentConfig(
            temperature=0, thinking_config=types.ThinkingConfig(thinking_level="minimal"))
        last_error: Exception | None = None
        for model in self.models:
            try:
                r = await self.client.aio.models.generate_content(model=model, contents=parts, config=config)
                return parse_json(r.text or "")
            except errors.ClientError as e:
                if e.code == 400:
                    raise BadInput(str(e)[:300]) from e
                last_error = e
            except (errors.ServerError, json.JSONDecodeError) as e:
                last_error = e
        raise last_error


class OllamaGemma:
    def __init__(self, url: str, model: str, transport: httpx.AsyncBaseTransport | None = None):
        self.url = url.rstrip("/")
        self.model = model
        self.transport = transport
        self.name = f"ollama:{model}"

    async def generate_json(self, prompt, schema, image=None, mime="image/jpeg"):
        message = {"role": "user", "content": prompt}
        if image:
            message["images"] = [base64.b64encode(image).decode()]
        body = {"model": self.model, "messages": [message], "format": schema, "stream": False,
                "think": False, "options": {"temperature": 0}}
        async with httpx.AsyncClient(timeout=300, transport=self.transport) as client:
            r = await client.post(f"{self.url}/api/chat", json=body)
        if r.status_code == 400:
            raise BadInput(r.text[:300])
        r.raise_for_status()
        return parse_json(r.json()["message"]["content"])


def make_gemma(settings) -> Gemma:
    if settings.llm_backend == "ollama":
        return OllamaGemma(settings.ollama_url, settings.ollama_model)
    return GeminiGemma(settings.gemini_api_key, settings.gemma_model, settings.gemma_fallback_model)
