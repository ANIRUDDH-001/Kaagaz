# Kaagaz — काग़ज़

**A voice-first helper for the parent who handles the household's important papers.**
Photograph a paper or say what it is, in Hindi, Hinglish or English. Kaagaz explains it in simple Hindi,
reads back what must be done (amount, last date, consequence), and after you confirm, it follows through:
reminders 30, 7 and 1 days before, and a message to the son if it still isn't done.

Built for the DEV Hacktoberfest 2026 "Build for a Friend" challenge.
**Live demo:** <your Render static site URL> · sample papers only.

## How it works

Understand → confirm → remember → follow through → escalate.

- **Gemma 4** reads the paper or the spoken instruction and returns structured actions. Every amount and date
  carries the exact words it came from; if the digits aren't in those words, the field is highlighted for checking.
- **Nothing is saved without a confirmation tap.**
- **Temporal Cloud** runs one durable workflow per obligation: timers that last months, retries, and signals for
  "done" and "remind me later". The workflow escalates, never the model.
- **MongoDB Atlas** holds obligations, history and the inbox. Photos and recordings are never stored.
- **ElevenLabs** transcribes Hinglish speech (Scribe v2) and speaks the Hindi readbacks (Flash v2.5).
- **Render** hosts the static app (always on) and the API (sleeps when idle). A GitHub Actions job runs the
  reminder worker four times an hour, so reminders arrive even while the API sleeps.

## Two modes, one codebase

| | Public demo | Private (family laptop) |
|---|---|---|
| Gemma | Gemma 4 26B via the Gemini API | Gemma 4 E4B via Ollama, on CPU |
| Speech-to-text | ElevenLabs Scribe v2 | faster-whisper large-v3-turbo |
| Voice | ElevenLabs | Browser |
| Photos and voice leave the device? | Yes — use sample papers only | No; only confirmed reminder details are synced |

Switch with `LLM_BACKEND`, `STT_BACKEND`, `TTS_BACKEND`, `APP_MODE` (see `.env.example`).

## Measured, not assumed

`python -m eval.run_eval` scores any backend on four synthetic papers and four spoken instructions.
Results: see `eval/results-gemini.md` and `eval/results-ollama.md`.

## Run it locally

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt   # add requirements-local.txt for private mode
cp .env.example .env   # fill in MongoDB Atlas, Temporal Cloud, Gemini, ElevenLabs, VAPID keys
.venv/Scripts/python -m pytest
.venv/Scripts/python -m uvicorn app.main:app --port 8000   # open http://localhost:8000
```

## Deploy

`render.yaml` defines the API (free web service) and the app (free static site). Set the `sync: false`
values in the Render dashboard, and the same secrets in GitHub Actions for `reminder-worker.yml`.

## License

MIT
