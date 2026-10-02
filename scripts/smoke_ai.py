"""One live call per configured AI backend. Uses .env; prints results, never keys.
  python -m scripts.smoke_ai [path-to-voice-clip]"""
import asyncio
import sys
import time
from datetime import date
from pathlib import Path

from ai.gemma import make_gemma
from ai.stt import make_stt
from ai.tts import make_tts
from ai.understand import plan_speech, read_paper
from app.config import get_settings
from tests.fakes import mock_store

TODAY = date(2026, 10, 2)


async def main() -> None:
    s = get_settings()
    gemma = make_gemma(s)
    t0 = time.time()
    card = await read_paper(gemma, Path("eval/photos/motor_renewal.jpg").read_bytes(), "image/jpeg", TODAY)
    print(f"[{gemma.name}] paper {time.time() - t0:.1f}s -> {card['readback_hi']} needs_check={card['actions'][0]['needs_check']}")
    if len(sys.argv) > 1:
        stt = make_stt(s)
        t0 = time.time()
        text = await stt.transcribe(sys.argv[1], "audio/mp4")
        print(f"[{stt.name}] {time.time() - t0:.1f}s -> {text}")
        card = await plan_speech(gemma, text, [], TODAY)
        print(f"[{gemma.name}] plan -> {card['readback_hi']}")
    tts = make_tts(s, mock_store())
    if tts:
        mp3 = await tts.synthesize("पापा, गाड़ी का इंश्योरेंस 7 दिन में due है।")
        Path("D:/tmp/smoke_tts.mp3").write_bytes(mp3)
        print(f"[tts] {len(mp3) // 1024} KB -> D:/tmp/smoke_tts.mp3")


if __name__ == "__main__":
    asyncio.run(main())
