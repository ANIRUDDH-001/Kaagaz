# Kaagaz — Important Papers Guardian: design spec

Date: 2026-10-02. Deadline: submit by 2026-10-05 12:29 IST (06:59 UTC).
Challenge: DEV Hacktoberfest 2026 Weekend Challenge, "Build for a Friend".

## 1. What it is

A voice-first web app for a parent who handles the household's important papers.
He photographs a paper or speaks an instruction in Hindi, Hinglish or English. The
app explains the paper in simple Hindi, works out what must be done (action, amount,
deadline, consequence), reads that back for confirmation, then follows it through:
reminders 30, 7 and 1 days before the deadline, and if he still hasn't marked it
done, it tells his son.

The loop is **understand → confirm → remember → follow through → escalate**.
The OCR is a means; the follow-through is the product.

### Users

- **Parent** (primary): reads Hindi comfortably, English partially; uses a phone;
  prefers speaking to typing.
- **Son** (secondary): lives elsewhere; wants to know only when something is
  about to slip.

### In scope (V1)

Paper types: insurance (motor, health, life), utility bills (electricity, water,
gas), school or college fees, property tax, certificate or licence renewals.
Anything else is extracted as `other` and handled the same way.

### Out of scope (V1)

Payments, bank integrations, multi-page PDFs, WhatsApp or Telegram, multiple
households per login, user accounts with passwords, Sentry, Mastra.

## 2. Hard rules

1. **Never invent a fact.** Amount, due date and consequence come only from the
   paper or the user's words. Each extracted field carries the exact source text
   it came from (`evidence`). A field with no evidence is `null`, and the app
   asks: "तारीख़ नहीं मिली — काग़ज़ पर देखकर बताइए।"
2. **Nothing is saved without confirmation.** Every extraction or voice
   instruction becomes a confirmation card with a spoken Hindi readback. Only
   the confirm tap writes to the database and starts a workflow.
3. **Real papers never go through the public demo.** The public site shows a
   banner saying it uses Google's hosted Gemma and is for sample papers only.
   Real family papers use private mode (section 7).
4. **Temporal never sees content.** Workflow inputs and signals carry IDs and
   dates only. Titles, amounts and text live in MongoDB.

## 3. User journey

Home screen: three large buttons, Hindi first with English below.

- **बोलिए / Speak** — hold to record (max 30 s).
- **काग़ज़ दिखाइए / Scan paper** — opens the phone camera, or picks a photo.
- **पूछिए / Ask** — a spoken question ("बिजली का बिल कब तक भरना है?").

Below them: "आगे क्या है" (what's next), a list of open items sorted by due date,
and the inbox of reminders.

### Flow A: scan a paper

1. Photo uploaded. Screen shows "काग़ज़ पढ़ रहा हूँ…" with progress.
2. Gemma extracts fields plus evidence and a two-sentence Hindi summary.
3. Confirmation card: title, amount, due date, action, consequence, each with
   its evidence line in small text. The Hindi readback plays:
   "गाड़ी का इंश्योरेंस, ₹18,400, आख़िरी तारीख़ 14 दिसंबर। सही है?"
4. Buttons: **सही है** (confirm), **बदलें** (edit any field), **रद्द** (discard).
5. On confirm: obligation saved, workflow started, "आगे क्या है" updates.

### Flow B: speak an instruction

1. Audio recorded with MediaRecorder, sent to speech-to-text.
2. Gemma turns the transcript into an action plan: a list of tool calls (section 5),
   given the household's open obligations so "LIC वाला reminder" resolves to an ID.
3. Confirmation card lists each planned action in Hindi. Confirm runs them all.

### Flow C: ask

1. Question by voice or text.
2. App loads the household's obligations (and completed history), Gemma answers
   in Hindi using only those records, citing which item it used.
3. Answer is shown and spoken. If the records don't contain the answer, it says so.

### Flow D: reminder and escalation

1. At each reminder point a notification arrives: Web Push to the parent's phone
   (if permitted) and an inbox item in the app. Text example:
   "पापा, गाड़ी का इंश्योरेंस 7 दिन में due है — ₹18,400।"
2. Opening it plays the Hindi voice and shows **हो गया** (done) and
   **बाद में याद दिलाना** (remind me on a date).
3. If the item is still not marked done 6 hours after the 1-day reminder
   (snoozing doesn't count), the son gets a push and inbox item: "Papa hasn't marked the car insurance (₹18,400, due 14 Dec) as done."
   The son can mark it done, or snooze it on the parent's behalf.

## 4. Architecture

```
Browser (PWA, vanilla JS)
  │  photo / audio / text, confirm, done, snooze
  ▼
Render free web service: FastAPI app  ──────────────►  MongoDB Atlas M0
  │   ├─ serves the PWA                                 (households, obligations,
  │   ├─ REST API                                        notifications, push subs,
  │   └─ Temporal worker (same process)                  tts cache)
  │                 ▲
  ▼                 │ polls task queue
Temporal Cloud ─────┘◄──── GitHub Actions cron worker (every 15 min, runs ~3 min)
  (workflow state, timers, retries)
  │
  activities call out to:
    ├─ Gemma: Gemini API (gemma-4-26b-a4b-it, fallback gemma-4-31b-it) | Ollama gemma4:e4b
    ├─ STT:   ElevenLabs Scribe v2 | faster-whisper large-v3-turbo
    ├─ TTS:   ElevenLabs (cached) | browser speechSynthesis
    └─ Web Push (VAPID, pywebpush)
```

### Why each piece exists

- **Gemma 4**: every understanding step: paper → fields, speech transcript →
  action plan, question → answer, Hindi summaries and readbacks.
- **MongoDB Atlas**: the household's memory. Flexible paper fields suit a
  document store; the Ask flow queries it.
- **Temporal Cloud**: durable timers measured in months, signals for done or
  snooze, and retries for flaky Gemma calls (we measured 500/503s on the free API).
- **ElevenLabs**: Scribe for Hinglish speech-to-text (best in our tests), and
  Hindi voice for readbacks and reminders.
- **Render**: hosts the live demo.

### Reminder delivery when Render is asleep

Render's free service sleeps after 15 minutes idle, so it can't be responsible
for reminders. Temporal Cloud holds every timer. When a timer fires, the work
waits in Temporal's task queue until any worker polls. Two workers poll:

1. The worker inside the Render process, whenever the site is awake (covers live
   demos, where timings are in seconds).
2. A GitHub Actions scheduled job every 15 minutes that runs the worker for
   about 3 minutes and exits. It covers real reminders while Render sleeps. Real
   reminders are scheduled for 09:00 IST, so they arrive by about 09:15–09:30
   (GitHub can delay cron runs).

Reminder activities don't call Gemma: the reminder text is written at confirm
time and stored. So the cron worker needs only Atlas, Temporal and VAPID secrets.

The same scheduled job may also request the site's home page so judges don't hit
a cold start. That's a convenience; no correctness depends on it.

## 5. Agent tools

Gemma returns a plan as JSON (schema-constrained), a list of these calls. The
app validates each call, shows it on the confirmation card, and executes on
confirm. These are the only ways Gemma can change state.

| Tool | Arguments | Effect |
|---|---|---|
| `create_obligation` | title, category, amount_inr?, due_date?, action, consequence?, evidence, remind_offsets_days (default [30,7,1]), escalate (default true) | Insert obligation, start `ObligationWorkflow` |
| `update_obligation` | obligation_id, changed fields | Update record; signal `update` if date changed |
| `mark_done` | obligation_id, note? | Status done; signal `mark_done` |
| `snooze` | obligation_id, until (YYYY-MM-DD) | Signal `snooze` |
| `answer` | text_hi, used_obligation_ids | Show and speak an answer (no state change) |
| `clarify` | question_hi | Ask the user something; no state change |

`search_memory` is not a tool Gemma calls. The app always passes the open
obligations (id, title, due date, amount) in the prompt; the household has at
most dozens of items, so this fits easily. `escalate` is not a tool either: the
workflow does it, not the model.

Dates are resolved against today's date in IST, passed in every prompt.

## 6. Data model (MongoDB)

- **households**: `_id`, `mode` (`demo` | `real`), `created_at`, `expires_at`
  (demo only; TTL index deletes demo data after 48 h), `members`:
  `[{role: "parent" | "son", name, push_subscriptions: [...]}]`.
- **obligations**: `_id`, `household_id`, `title`, `title_hi`, `category`,
  `amount_inr`, `due_date`, `action`, `consequence`, `evidence`
  (`{amount, due_date, consequence}` source strings), `summary_hi`,
  `remind_offsets_days`, `escalate`, `status` (`active` | `done` | `cancelled`),
  `snoozed_until`, `workflow_id`, `source` (`photo` | `voice` | `text`),
  `history` (`[{at, by_role, event, detail}]`), `created_at`.
- **notifications**: `_id`, `household_id`, `to_role`, `obligation_id`, `kind`
  (`reminder` | `escalation`), `text_hi`, `text_en`, `created_at`, `read_at`.
- **tts_cache**: `_id` (sha256 of voice + text), `mp3` (binary), `created_at`.

Photos and audio are never written to the database (see `kaagaz-ai` in section 8).
Only the extracted fields and evidence strings are stored.

## 7. Two modes, one codebase

Selected by environment variables. Same prompts, same schemas, same workflows.

| | Public demo (Render) | Private (family laptop) |
|---|---|---|
| Gemma | Gemini API `gemma-4-26b-a4b-it` → `gemma-4-31b-it` on 429/5xx | Ollama `gemma4:e4b` on CPU |
| Speech-to-text | ElevenLabs Scribe v2 | faster-whisper large-v3-turbo, `language="hi"` |
| Voice out | ElevenLabs (cached by text) | Browser `speechSynthesis` (hi-IN) |
| Papers and audio leave the device? | Yes, to Google and ElevenLabs. Sample papers only | No |
| Database, Temporal | Atlas, Temporal Cloud | Same; they hold only extracted fields and IDs |

Honest claim for the write-up: in private mode the paper photo and the voice
never leave the laptop; only the confirmed reminder fields are stored in Atlas.

Env vars: `LLM_BACKEND=gemini|ollama`, `STT_BACKEND=elevenlabs|whisper`,
`TTS_BACKEND=elevenlabs|browser`, `MONGODB_URI`, `TEMPORAL_ADDRESS`,
`TEMPORAL_NAMESPACE`, `TEMPORAL_API_KEY`, `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`,
`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `APP_MODE=demo|real`.

## 8. Temporal workflows

Two task queues:

- `kaagaz-ai`: processing uploads. Polled only by the server process that
  received the upload (the Render web process, or the laptop in private mode),
  because the upload sits on that machine's local disk.
- `kaagaz`: reminders and escalations. Polled by the Render process and the
  GitHub Actions job; these activities need only Atlas and VAPID keys.

### `ProcessInputWorkflow(household_id, input_id, kind)` on `kaagaz-ai`

Runs the slow, flaky part. Activities: `transcribe` (voice only), `gemma_plan`
(or `gemma_extract` for photos). Retry policy: initial 5 s, backoff 2×, max 5
attempts, non-retryable on 400 (bad input). The raw upload is a temp file on the
receiving server, deleted when the workflow finishes; it is never written to
Mongo. If the server restarted and the file is gone, the card says "please send
it again". The browser polls `GET /api/inputs/{id}` for the confirmation card.

### `ObligationWorkflow` on `kaagaz`

Arguments: `obligation_id, household_id, due_date, offsets, schedule`.
`schedule` is `real` or `demo`.

- **real**: reminders at 09:00 IST on due − 30, due − 7 and due − 1 days
  (skipping points already past; if all are past, one reminder now).
  Escalation at 15:00 IST on due − 1 if not done.
- **demo**: the same sequence compressed for a live visitor: reminders at
  +30 s, +60 s, +90 s after confirm, escalation at +3 min. Each notification
  says which real reminder it stands for ("30 दिन पहले वाला reminder").

Loop: `workflow.wait_condition(changed_or_done, timeout=until_next_point)`.
Signals: `mark_done`, `snooze(until)`, `update(due_date)`, `cancel`.
Query: `next_event` (for the "next reminder" line in the UI).
Activities: `send_reminder(obligation_id, point)` and
`send_escalation(obligation_id)`. Each writes a notification document and sends
Web Push to that role's subscriptions; 410 Gone removes the subscription.
After `snooze(until)`, the next reminder is at 09:00 IST on `until`, then the
normal points that remain; escalation still applies.

## 9. Model prompts and safety

- Prompts and JSON schemas carry over from the spike (`_spike/common.py`), with
  `evidence` fields added and the rule "if the paper doesn't show it, return null".
- Ollama calls use `format` (JSON schema), `think: false`, temperature 0.
  Gemini calls use temperature 0, 180 s timeout, JSON parsed from the reply.
- Server-side validation after Gemma: amount positive and below ₹1 crore,
  due date a real date within 2 years, `obligation_id` exists in this household.
  Failures become a `clarify` card, not an error.
- Rate protection: free tier is 30 requests a minute and 16,000 tokens a minute
  per model. Each demo household gets at most 15 Gemma calls an hour; the UI
  says so when the limit is hit.

## 10. Demo design (live deployment is the demo)

- First visit creates a demo household (cookie), expiring after 48 h. No login.
- "Try a sample paper" offers the four specimen papers (motor insurance,
  electricity bill, school fee, property tax), as phone-style photos.
- A **role switch** (Papa / Son) at the top, so one visitor can watch the
  escalation arrive on the son's side. Push works for both roles in one browser.
- Demo obligations use the `demo` schedule, so a visitor sees reminders and the
  escalation within 3 minutes.
- A "How it works" page shows the architecture and the accuracy table (section 11).

## 11. Evaluation (published in the repo)

`eval/` holds the four synthetic papers, phone-style photos, four voice-clip
transcripts, ground truth and a runner that scores any backend. Results go in
the README and the post. Spike baseline (to be rerun with the final prompts):

| Backend | Photo fields | Voice instructions | Speed |
|---|---|---|---|
| Hosted Gemma 4 26B | 20/20 | all correct | 20–35 s |
| Local Gemma 4 E4B (CPU) | 18/20 | 9/11 | 21–27 s photo, 7–9 s voice |
| Local Gemma 4 E2B (CPU) | 15/20, one invented consequence | weak | 13–15 s |

Speech-to-text: Scribe v2 near-perfect on all clips; Whisper large-v3-turbo
correct when forced to Hindi; Whisper small and base misheard the amount.

## 12. Stack and repo

- Python 3.11+, FastAPI, Uvicorn, `temporalio`, `pymongo` (async), `google-genai`,
  `httpx`, `pywebpush`, `faster-whisper` (private mode only, optional extra).
- Frontend: static HTML, CSS and vanilla JS modules served by FastAPI, with a
  manifest and service worker (push and installability). No build step.
- Repo layout:

```
kaagaz/
  app/        main.py, api routes, config, db, schemas
  ai/         gemma backends, stt backends, tts, prompts
  flows/      workflows, activities, worker.py (with --drain-seconds)
  web/        index.html, app.js, styles.css, sw.js, manifest.json, samples/
  eval/       papers, photos, ground_truth.json, run_eval.py
  tests/
  .github/workflows/  ci.yml, reminder-worker.yml
  render.yaml, README.md, LICENSE (MIT)
```

## 13. Testing

- **Unit**: schema validation, date resolution, reminder-point calculation
  (past points skipped, snooze, IST 09:00), validation rules.
- **Workflow**: `WorkflowEnvironment.start_time_skipping()` runs
  `ObligationWorkflow` across 30 days in seconds; asserts reminders at each
  point, no escalation after `mark_done`, escalation when ignored, snooze moves
  the next reminder.
- **AI**: a fake Gemma backend for unit tests; `eval/run_eval.py` for the
  real models.
- **CI**: GitHub Actions runs tests on push.

## 14. Acceptance tests (MVP is done when all pass on the live URL)

1. **Infrastructure proof (first build task)**: a deployed skeleton on Render
   starts a workflow with a 20-minute timer, Render is left to sleep, and the
   reminder notification is still delivered by the GitHub Actions worker.
2. A sample motor-insurance photo produces a confirmation card with ₹18,400 and
   14 Dec 2026, each with evidence text, and a spoken Hindi readback.
3. Confirming it creates the obligation and shows the next reminder date.
4. In the demo schedule, three reminders arrive within 90 s, and the son's view
   gets the escalation at 3 min if nothing is marked done.
5. Marking it done (as parent or son) stops all further notifications.
6. With an LIC obligation already saved, the spoken Hinglish clip "LIC wala
   reminder Friday tak aage kar do" produces a snooze of that obligation to the
   next Friday, after confirmation.
7. "बिजली का बिल कब तक भरना है?" is answered in Hindi from stored records.
8. A photo with the date covered yields `due_date: null` and a clarify prompt,
   not an invented date.
9. With `LLM_BACKEND=ollama STT_BACKEND=whisper TTS_BACKEND=browser`, flows A–C
   work on the laptop with the network to Google and ElevenLabs blocked.
10. Usable on a phone-width screen (360 px).

## 15. Schedule

- **Fri 2 Oct (night)**: spec and plan approved; repo; accounts; acceptance
  test 1 (the infrastructure proof).
- **Sat 3 Oct**: extraction, voice, confirmation, workflows, inbox, push, UI.
- **Sun 4 Oct**: private mode, eval rerun, polish, README, DEV post draft.
- **Mon 5 Oct, by 10:00 IST**: final checks and submit (deadline 12:29 IST).
