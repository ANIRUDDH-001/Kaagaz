"""Synthetic-voice clips for the speech eval: ElevenLabs reads each line (two voices), then background noise is
mixed in at 15 dB SNR. These are labelled synthetic in the results; they test the STT -> Gemma path, not a real
elderly voice. Run once; the WAVs are kept so later runs are repeatable.

  python -m eval.make_audio --voices <voice_id_0>,<voice_id_1>"""
import argparse
import asyncio
import json
import tempfile
import wave
from pathlib import Path

import httpx
import numpy as np

from app.config import get_settings

ROOT = Path(__file__).parent
API = "https://api.elevenlabs.io"
RATE = 16000


def noise(n: int, rng) -> np.ndarray:
    """Pink-ish room noise plus a faint 50 Hz mains hum."""
    white = rng.normal(0, 1, n)
    spec = np.fft.rfft(white)
    spec /= np.sqrt(np.arange(1, len(spec) + 1))
    pink = np.fft.irfft(spec, n)
    hum = 0.3 * np.sin(2 * np.pi * 50 * np.arange(n) / RATE)
    x = pink / (np.std(pink) + 1e-9) + hum
    return x / (np.std(x) + 1e-9)


def mix(speech: np.ndarray, snr_db: float, rng) -> np.ndarray:
    n = noise(len(speech), rng)
    scale = np.sqrt(np.mean(speech ** 2) / (10 ** (snr_db / 10)))
    out = speech + scale * n
    return (out / max(1.0, np.max(np.abs(out)))).astype(np.float32)


async def main() -> None:
    from faster_whisper.audio import decode_audio

    ap = argparse.ArgumentParser()
    ap.add_argument("--voices", required=True, help="two ElevenLabs voice ids, comma separated")
    voices = ap.parse_args().voices.split(",")
    s = get_settings()
    cases = json.loads((ROOT / "ground_truth.json").read_text(encoding="utf-8"))["audio"]
    (ROOT / "audio").mkdir(exist_ok=True)
    rng = np.random.default_rng(2026)
    async with httpx.AsyncClient(timeout=90, headers={"xi-api-key": s.elevenlabs_api_key}) as c:
        for name, case in cases.items():
            r = await c.post(f"{API}/v1/text-to-speech/{voices[case['voice']]}",
                             json={"text": case["text"], "model_id": "eleven_multilingual_v2"},
                             params={"output_format": "mp3_44100_64"})
            r.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=r"D:\tmp") as f:
                f.write(r.content)
            speech = decode_audio(f.name, sampling_rate=RATE)
            Path(f.name).unlink()
            pcm = (mix(speech, 15.0, rng) * 32767).astype("<i2")
            with wave.open(str(ROOT / "audio" / f"{name}.wav"), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(RATE)
                w.writeframes(pcm.tobytes())
            print("wrote", name)


if __name__ == "__main__":
    asyncio.run(main())
