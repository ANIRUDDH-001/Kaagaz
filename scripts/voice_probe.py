"""Which ElevenLabs model and voice say "10 अक्टूबर" without dragging it out? Measures, doesn't guess.

  .venv\\Scripts\\python -m scripts.voice_probe
Writes clips to D:\\tmp\\voice_probe and prints one row per model x voice: the clip's length, how long Whisper
says "अक्टूबर" lasts, and what Whisper heard. Reads the API key through settings; never prints it."""
import asyncio
import time
from pathlib import Path

import httpx

from app.config import get_settings

OUT = Path(r"D:\tmp\voice_probe")
TEXT = "बिजली का बिल, ₹2,346, आख़िरी तारीख़ 10 अक्टूबर। सही है?"
MODELS = ["eleven_flash_v2_5", "eleven_multilingual_v2"]
API = "https://api.elevenlabs.io"


async def main() -> None:
    from faster_whisper import WhisperModel

    s = get_settings()
    OUT.mkdir(parents=True, exist_ok=True)
    headers = {"xi-api-key": s.elevenlabs_api_key}
    async with httpx.AsyncClient(timeout=90, headers=headers) as c:
        voices = (await c.get(f"{API}/v2/voices", params={"page_size": 30})).json()["voices"]
        print("voices on the account (id, name, labels):")
        for v in voices:
            print(" ", v["voice_id"], v["name"], v.get("labels"))
        # The account's first voice (today's default) against calm, clear premade voices.
        calm = ("River", "Alice", "Matilda", "Brian")
        picks = [voices[0]] + [v for v in voices[1:] if v["name"].split(" ")[0] in calm]
        whisper = WhisperModel("large-v3-turbo", device="auto", compute_type="auto")
        print("\n| model | voice | clip s | अक्टूबर s | heard |")
        for model in MODELS:
            for v in picks:
                body = {"text": TEXT, "model_id": model}
                if "flash" in model:
                    body["language_code"] = "hi"
                r = await c.post(f"{API}/v1/text-to-speech/{v['voice_id']}", json=body,
                                 params={"output_format": "mp3_44100_64"})
                if r.status_code != 200:
                    print(f"| {model} | {v['name']} | error {r.status_code} | | |")
                    continue
                path = OUT / f"{model}__{v['voice_id']}.mp3"
                path.write_bytes(r.content)
                segments, info = whisper.transcribe(str(path), language="hi", word_timestamps=True)
                words = [w for seg in segments for w in seg.words]
                heard = "".join(w.word for w in words).strip()
                oct_s = max((w.end - w.start for w in words if "क्ट" in w.word or "क्त" in w.word), default=-1)
                print(f"| {model} | {v['name']} ({v['voice_id']}) | {info.duration:.2f} | {oct_s:.2f} | {heard} |")
                time.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
