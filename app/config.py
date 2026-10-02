"""Settings read once from the environment (.env locally, dashboard env vars on Render)."""
import os
from dataclasses import dataclass, fields
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

CHOICES = {
    "app_mode": {"demo", "real"},
    "llm_backend": {"gemini", "ollama"},
    "stt_backend": {"elevenlabs", "whisper"},
    "tts_backend": {"elevenlabs", "browser"},
}


@dataclass(frozen=True)
class Settings:
    app_mode: str = "demo"
    llm_backend: str = "gemini"
    stt_backend: str = "elevenlabs"
    tts_backend: str = "elevenlabs"
    mongodb_uri: str = ""
    mongodb_db: str = "kaagaz"
    temporal_address: str = ""
    temporal_namespace: str = "default"
    temporal_api_key: str = ""
    gemini_api_key: str = ""
    gemma_model: str = "models/gemma-4-26b-a4b-it"
    gemma_fallback_model: str = ""
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma4:e4b"
    elevenlabs_api_key: str = ""
    elevenlabs_tts_model: str = "eleven_multilingual_v2"   # flash garbled Hindi dates (probe, 2026-10-02)
    elevenlabs_voice_id: str = "SAz9YHcvj6GT2YYXdXww"       # "River", a premade voice; ids are public
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@example.com"
    frontend_origin: str = "http://localhost:8000"   # comma-separated if the site has more than one address
    upload_dir: str = ""


@lru_cache
def get_settings() -> Settings:
    values = {}
    for f in fields(Settings):
        raw = os.environ.get(f.name.upper())
        if raw:
            values[f.name] = raw.strip()
    s = Settings(**values)
    for name, allowed in CHOICES.items():
        if getattr(s, name) not in allowed:
            raise ValueError(f"{name.upper()} must be one of {sorted(allowed)}")
    return s
