# Kaagaz काग़ज़

**Kaagaz understands, remembers and protects.**
Show it a bill, notice or message, or just say what it is, in Hindi, Hinglish or English. Kaagaz explains it,
reads back what must be done, reminds before the date, tells the son if it slips, and warns when a "bill" is
really a scam.

Built for the DEV Hacktoberfest 2026 "Build for a Friend" challenge, for a parent who handles the family's papers.
**Live demo:** https://kaagaz-bx24.onrender.com (fictitious sample papers only). **How it works:** `web/how.html`.

## What it does

- **Understands papers and messages.** A photo of a bill, renewal notice, fee notice or SMS/WhatsApp screenshot, or a
  spoken instruction. Gemma 4 returns the amount, the last date, what to do and what happens if it's missed, each
  with the exact words it came from. Anything the words don't support is outlined for checking.
- **Confirms before it saves.** A card reads it back aloud, in English or Hindi. Nothing is saved without the tap.
- **Remembers.** Reminders 30, 7 and 1 days before, or on the day he picks with "Later" (tomorrow, in 3 days, next
  week, or a date). If it still isn't done, the son gets an alert.
- **Protects.** Every scan is checked for seven scam warning signs (personal UPI or account, payment links, OTP
  requests, remote-access apps, threats within hours, "call this mobile", prizes and refunds). Each sign quotes the
  words that raised it, and the server checks those words before showing it. It never says "safe". One tap tells the son.
- **Carries renewals forward.** Insurance, property tax and certificate renewals are offered again for next year when
  marked done, showing last year's amount instead of guessing the new one.
- **English first, Hindi one tap away.** Every label, message, readback and error exists in both; the choice is
  remembered per device. Light paper theme by default, with a dark toggle.

## Measured, not assumed

Scored on 26 fictitious documents (6 of them scams), each in 4 simulated photo conditions, plus 20 typed and 8
synthetic-voice instructions. Gemma 4 26B (the public demo):

| What was measured | Result |
|---|---|
| Paper fields exactly right (amount, date, category, consequence, Hindi summary) | **412/412** |
| Wrong amounts or dates that were not highlighted | **0** |
| Scam messages given the red warning | **24/24** (6 scams × 4 conditions) |
| Genuine papers wrongly given the red warning | **0 of 80** |
| Typed instructions fully right | **20/20** |
| Spoken clips (synthetic voice + noise) fully right | **8/8** |
| Time per call | median 9.7 s, 90th percentile 13.4 s |

The documents are cleanly typeset and the scams are textbook ones, so real crumpled papers and cleverer scams will
be harder; that's why every fact carries its evidence and nothing is saved without a tap. The laptop model
(Gemma 4 E4B) scored 18/20 fields with one silent error on the earlier 4-paper set; its full run on this set was
not completed for this submission.

Full tables: [`eval/results-gemini.md`](eval/results-gemini.md), [`eval/results-ollama.md`](eval/results-ollama.md).
Method and what is simulated: [`eval/README.md`](eval/README.md).

## How it's built

Understand → confirm → remember → follow through → protect.

- **Gemma 4** reads the paper or the instruction and returns structured actions plus scam signs with evidence.
  The server checks every fact against its evidence before the card is shown.
- **Temporal Cloud** runs one durable workflow per paper: timers that last months, retries, and signals for "done"
  and "later". The workflow escalates, never the model. Workflows carry only IDs and dates.
- **MongoDB Atlas** holds papers, history and the inbox. Photos and recordings are never stored.
- **ElevenLabs** transcribes Hinglish speech and speaks the readbacks (`eleven_multilingual_v2`, voice River;
  amounts are spoken as "18400 rupees" rather than "R S").
- **Render** hosts the static app and the API. A GitHub Actions job runs the reminder worker four times an hour, so
  reminders arrive even while the free API sleeps.

## Two modes, one codebase

| | Public demo | Private (family laptop) |
|---|---|---|
| Gemma | Gemma 4 26B via the Gemini API | Gemma 4 E4B via Ollama |
| Speech to text | ElevenLabs Scribe | faster-whisper |
| Voice | ElevenLabs | The browser |
| Photos and voice leave the device? | Yes, so use the sample papers | No; only confirmed reminder details sync |

Switch with `LLM_BACKEND`, `STT_BACKEND`, `TTS_BACKEND` and `APP_MODE` (see `.env.example`).

## Run it locally

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt   # add requirements-local.txt for private mode
cp .env.example .env   # MongoDB Atlas, Temporal Cloud, Gemini, ElevenLabs and VAPID keys
.venv/Scripts/python -m pytest
.venv/Scripts/python -m uvicorn app.main:app --port 8000   # open http://localhost:8000
```

Run the eval:

```bash
.venv/Scripts/pip install -r requirements-eval.txt
.venv/Scripts/python -m eval.make_docs && .venv/Scripts/python -m eval.render_docs
.venv/Scripts/python -m eval.make_audio --voices SAz9YHcvj6GT2YYXdXww,XrExE9yKIg1WjnnlVkGX
.venv/Scripts/python -m eval.run_eval
```

## Deploy

`render.yaml` defines the API (free web service) and the app (free static site). Set the `sync: false` values in the
Render dashboard: `FRONTEND_ORIGIN` must be the static site's address (comma-separated if it has more than one), and
set `ELEVENLABS_TTS_MODEL=eleven_multilingual_v2` and `ELEVENLABS_VOICE_ID=SAz9YHcvj6GT2YYXdXww` for the voice.
Put the same secrets in GitHub Actions for `reminder-worker.yml`.

## License

MIT
