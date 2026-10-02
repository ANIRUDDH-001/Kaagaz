# Kaagaz v2: understand, remember, protect

Date: 2026-10-02. Builds on `2026-10-02-kaagaz-design.md`, which stays the authority for everything
this document does not change. Deadline: submit by 2026-10-05 12:29 IST.

## 1. Why v2

V1 works end to end, but a judge sees three weaknesses first: the UI looks like a prototype, the demo
says "reads a bill and reminds you" (a familiar idea), and the evidence that it works rests on four
clean printed papers. V2 keeps the core loop and fixes those three things.

The pitch becomes **"Kaagaz understands, remembers and protects."**

- **Understands:** a paper or a message screenshot, in English or Hindi (existing).
- **Remembers:** reminders before the deadline, the son told if it slips (existing), and yearly
  renewals carried forward (new).
- **Protects:** every scan is checked for scam warning signs, with the exact words as evidence (new).

Decisions already made with the user:

| Topic | Decision |
|---|---|
| Headline feature | Scam check plus yearly repeat |
| Scam check trigger | Automatic, inside every scan; no separate button |
| Visual direction | "Kaagaz paper" (warm paper, ink blue, stamp red) with "calm modern" spacing and contrast |
| Language | **English by default**, Hindi one tap away, remembered per device |
| Test photos | Code-made photo conditions (tilt, shadow, dim, crease, blur), labelled as simulated |

## 2. Hard rules (unchanged, extended)

V1's four hard rules stand. Two additions:

5. **A scam warning is evidence, never a verdict.** Every warning sign carries the exact words that
   triggered it, and the server checks those words before showing the sign. The app never says
   "safe". With no signs, it says nothing about scams at all.
6. **Both languages say the same thing.** Every message the server writes from a template has an
   English and a Hindi version. Model-written text (summary, answer, clarify question) is requested
   in both languages in the same call.

## 3. Language: English first, Hindi toggle

- The UI starts in English. A `EN | हिं` pill in the header switches every label, button, status and
  error. The choice is saved in `localStorage` (`kaagaz.lang`) and sets `<html lang>`.
  `?lang=hi` in the URL overrides it, so a demo link can open in Hindi.
- **Server text.** Every server-written string gets `_en` and `_hi` versions:
  - Card readback: `readback_en`, `readback_hi`, both from templates.
  - Reminders and escalations already have `text_en` and `text_hi`.
  - Clarify questions and fixed errors (`ActionError`, HTTP details, `ERRORS`): a single bilingual
    message table in `app/i18n.py`. Errors return `{"detail": {"en": ..., "hi": ...}}`.
  - Paper summary and spoken answers come from the model: the schemas gain `summary_en`, `text_en`
    and `question_en` next to the Hindi fields.
- **Voice out.** `/api/tts` takes `lang` (`en` | `hi`) and sends a matching `language_code`. The client
  speaks the readback in the current UI language, and the browser fallback picks a voice for that
  language.
- **Voice in.** Unchanged: he can speak Hindi, Hinglish or English whatever the UI language.
- English is written for an Indian user: "₹18,400", "14 Dec 2026", "Papa" and "Son" (role labels).

## 4. Scam check

### What it detects

The paper prompt now says the photo may be a paper **or a screenshot of an SMS, WhatsApp or e-mail**.
`PAPER_SCHEMA` gains:

```
"doc_type": "bill_or_notice" | "message" | "other",
"scam_signs": [ { "sign": <enum>, "evidence": "<exact words from the image>" } ]
```

| `sign` | Meaning | Server check on `evidence` (all must hold to show it) |
|---|---|---|
| `personal_payment` | Pay to a personal UPI ID, phone number or personal bank account | contains a UPI handle (`x@y`) or a 10-digit mobile number or an account number |
| `suspicious_link` | Pay or "update" through a shortened or unofficial link | contains a URL or a domain |
| `asks_secret` | Asks for an OTP, PIN, CVV or password | mentions OTP, PIN, CVV or password (in English or Hindi) |
| `remote_app` | Asks to install AnyDesk, TeamViewer, QuickSupport or an APK | names the app or ".apk" |
| `threat_deadline` | Threatens disconnection, arrest or a penalty within hours ("tonight", "within 2 hours") | contains an hour or "tonight/today/आज रात" word |
| `call_number` | Asks him to call or WhatsApp a mobile number to fix the problem | contains a 10-digit mobile number |
| `prize_refund` | A prize, lottery, KYC bonus or refund that needs a payment first | non-empty |

The server also checks that the evidence is short (at most 200 characters) and drops a sign that has
no evidence.

### Levels

- **Warning** (red): at least one of `personal_payment`, `suspicious_link`, `asks_secret`,
  `remote_app`, `prize_refund`, **or** both `threat_deadline` and `call_number`.
- **Caution** (amber): only `threat_deadline` or only `call_number`. Genuine bills also print
  helpline numbers and disconnection notices, so one weak sign alone stays amber.
- **None:** no scam UI at all.

### On the card

- **Warning:** a red stamp at the top reads "This doesn't look genuine", followed by each sign with its
  quoted evidence and fixed advice: "Don't pay, don't call, don't share an OTP. Check with the number
  on an old bill, or ask your son." The primary button becomes **Don't save**. Saving a reminder is
  still possible as a secondary "Save anyway" (he may know better). A **Tell my son** button sends
  the son a notification with the warning, through the existing inbox and push.
- **Caution:** an amber strip listing the sign, and the normal buttons.
- The readback (voice) starts with the warning in the current language.

### API

- The card's paper action gains `scam: {"level": "warning"|"caution"|"none", "signs": [...]}`.
- `POST /api/inputs/{id}/warn-son`: allowed only when that card's level is not `none`. It stores a
  son notification of kind `scam_warning` (title, the signs, no image) and sends push. Repeated calls
  for the same input are idempotent.

### Out of scope

Comparing phone numbers or UPI IDs with earlier bills, link reputation lookups, and reading text
messages without a screenshot.

## 5. Yearly repeat

- Recurring categories: `motor_insurance`, `health_insurance`, `life_insurance`, `property_tax`,
  `certificate_renewal`.
- When an obligation in one of those categories is marked done (button or voice), the response
  carries `repeat_offer: {"obligation_id", "due_date": <same day next year>}`. Feb 29 becomes Feb 28.
- The UI shows a sheet: "Remind you again next year? 14 Dec 2027", with **Yes** and **No**.
  **Yes** calls `POST /api/obligations/{id}/repeat`. That tap is the confirmation (hard rule 2).
- The repeat creates a new obligation:
  - same title, category, action and escalation;
  - `due_date` one year on, which must pass the same date window as create;
  - `amount_inr: null` and `last_amount_inr` kept, because next year's premium is unknown and we
    never invent it;
  - `repeat_of` set to the old id;
  - its workflow started exactly as a create does.

  The obligation id derives from the old one (`<old_id>-y<year>`), so a double tap creates one.
- "What's next" shows a small "every year" tag on obligations that have `repeat_of` or a recurring
  category.

## 6. Redesign

Vanilla HTML, CSS and JS, no build step, same files served by FastAPI and Render. The work uses
the `frontend-design` skill.

### Look

- Light paper background (`#f7f2e8`, with a subtle grain), ink text (`#1f2a44`), stamp red
  (`#b3261e`) for urgency and warnings, deep green (`#1d6b4f`) for done, and amber for caution.
  Text contrast meets WCAG AA.
- Type:
  - Fraunces for English display text, Inter for English body text.
  - Tiro Devanagari Hindi for Hindi display text, Mukta for Hindi body text.
  - Base size 17 px, and 48 px minimum touch targets.
- SVG line icons, no emoji. The motion is a gentle pulse while recording, a card that slides up, and a
  stamp "thunk" on confirm. All motion respects `prefers-reduced-motion`.
- A dark variant through `prefers-color-scheme` (ink background, paper text). It's the first thing
  cut if time runs short.

### Screens

1. **Header:** wordmark "Kaagaz काग़ज़", the `EN | हिं` pill, and a Papa/Son switch.
2. **First visit:** a dismissible strip with three steps ("Show a paper → Kaagaz explains and checks
   it → It reminds Papa, and tells his son if it slips") and the demo notice "Demo: use the
   sample papers, not real documents" as a calm chip, not an orange banner.
3. **Home:**
   - A greeting ("Hello Papa · 3 things coming up").
   - A large hold-to-speak button with a live timer, release to send.
   - Two secondary actions: Scan paper and Type a question.
4. **Working:** a step tracker instead of a spinner: Reading the paper → Checking for scam signs →
   Getting your card ready. It fills from the input's status.
5. **Confirmation card** ("stamped slip"):
   - A scam stamp, if any.
   - Title, a large amount and the due date with days left.
   - The action, then the consequence.
   - Evidence quotes under each field.
   - Fields that need checking are outlined amber and editable inline.
   - A speaker button replays the readback.
   - Buttons: Confirm (stamp animation), Edit, Discard.
6. **What's next:** a timeline sorted by due date.
   - Each item has a days-left badge: red at 7 days or less, amber at 30 or less, neutral otherwise.
   - It also shows a category icon, the next reminder and the "every year" tag.
   - Actions: **Done** and **Later**. Later opens a sheet with Tomorrow, In 3 days, Next week and Pick
     a date.
7. **Inbox:** reminders, escalations and scam warnings, each with Listen and Mark read.
8. **Samples:** a scrolling row of six, with real thumbnails loaded eagerly: four existing papers
   plus two suspicious messages ("Suspicious SMS", "WhatsApp offer").
9. **Waking:** a full-screen friendly state, "Waking up the assistant (free server, about a minute)",
   with progress.
10. **How it works** (`how.html`): restyled to match, English first, with the updated measurement
    tables.

### Product basics

- Every asset URL carries `?v=<version>`, and FastAPI sends `Cache-Control: no-cache` for HTML and
  long-lived caching for versioned assets. This fixes the deferred stale `app.js` minor.
- Loading, empty and error states exist for every list and action.
- Accessibility:
  - `aria-live` for status and card changes, visible focus rings, labels on icon buttons.
  - Target: Lighthouse accessibility score of at least 95.
- `app.js` is split into `i18n.js` (strings), `render.js` (HTML builders) and `app.js` (state and
  flows), so no file grows past what one person can hold in their head.

## 7. Voice glitch ("10 October" drawn out)

The text we send is clean ("10 अक्टूबर"), and `language_code=hi` is already set for the flash model.
The voice comes from `GET /v2/voices?page_size=1`, which is the account's first voice and probably an
English one. The fix is decided by measurement, not by ear:

- Generate the readback "…आख़िरी तारीख़ 10 अक्टूबर। सही है?" for each combination: model
  (`eleven_flash_v2_5`, `eleven_multilingual_v2`) × voice (the current default, two multilingual
  voices).
- Measure the audio length per character, and transcribe each clip back with Whisper, using
  word timestamps to find the duration of "अक्टूबर".
- Pick the combination where that word stays under 1.0 s and the transcript matches. Set it as the
  default model and voice in `.env.example` and `config.py` (a voice id, not a key).

The probe and its numbers go in the ledger.

## 8. Evaluation v2

### Papers

- The existing 4 HTML specimens grow to **about 20 genuine papers**. Every category is covered, plus
  these traps:
  - a bill date next to a due date;
  - an "after due date" amount next to the amount payable;
  - a rebate amount next to the payable amount;
  - several dates on one paper;
  - Hindi-only and English-only papers;
  - no due date at all (truth: `null`);
  - an already-paid receipt (truth: nothing due);
  - a genuine urgent disconnection notice (truth: scam level `none` or `caution`, never `warning`).
- **About 6 scam samples:**
  - a fake electricity-disconnection SMS with a personal number;
  - a fake KYC SMS with a link;
  - a fake traffic challan with a link;
  - a WhatsApp lottery message;
  - an "insurance bonus refund" message asking for an OTP;
  - a gas-connection threat with a personal UPI ID.

  Truth: level `warning` plus the expected signs.
- All data is fictitious, every document carries a "SPECIMEN" mark, phone numbers are obviously fake,
  and links use invented domains.
- Each document is rendered to an image by headless Edge, then given **4 simulated conditions** by a
  deterministic script (Pillow and NumPy, fixed seeds):
  1. clean;
  2. tilted with perspective and a shadow;
  3. dim and noisy with heavy JPEG compression;
  4. creased and slightly blurred.

  That gives about 104 images, all in `eval/photos/<doc>__<condition>.jpg`. Results label them
  "simulated photo conditions".

### Speech

- **About 20 typed utterances** (English, Hinglish in Latin script, Hindi in Devanagari) covering
  create, update, done, snooze, question, an ambiguous reference (expect clarify) and a mixed request.
- **About 8 audio clips:** a few of those utterances synthesized with two ElevenLabs voices and mixed
  with recorded-style background noise, then run through the real speech-to-text. They're labelled
  "synthetic voice".

### Metrics (per backend: hosted Gemma 26B and local E4B)

- Paper fields exactly right, overall and per condition.
- Silent errors: a wrong amount or date that the card did **not** highlight. This is the number that
  matters for safety.
- Scam detection: scam samples that reached `warning`, and signs found that match the expected ones.
- **False alarms:** genuine papers shown as `warning`. The target is 0, and any false alarm is listed
  by name.
- Spoken instructions fully right, separately for typed and audio.
- Median and 90th-percentile latency.

`eval/run_eval.py` gains `--subset` (for quick runs) and writes `eval/results-<backend>.md` with a
per-condition table. `how.html` shows the summary, including failures.

## 9. Testing

- TDD for every server change: bilingual readback, scam sign validation and levels, `warn-son`
  (allowed or refused, idempotent), repeat offer and repeat (Feb 29, double tap, window, workflow
  started, amount null), language-aware TTS, errors returned in both languages, cache headers.
- Eval scoring functions get unit tests (`tests/test_eval_scoring.py`).
- Frontend: browser checks at 375 px and desktop for each screen state, both languages, no
  horizontal scroll, keyboard reachable, and a Lighthouse accessibility run.
- A full suite run after each task. An end-to-end run on `:8000` with real Gemma, Temporal Cloud and
  Atlas covers a sample scam (warning, then Tell my son reaches the son's inbox) and a renewal (done,
  then next year, then a new workflow).

## 10. Order and cut line

1. The voice probe and fix.
2. Server: i18n, then the scam check, then yearly repeat.
3. Eval v2: the documents, the conditions script, the runner, and runs in the background.
4. Redesign: all the screens and both languages.
5. `how.html`, README and the e2e run.

Cut in this order if Sunday morning is tight: the dark variant, then audio speech eval, then
"Tell my son", then the redesigned `how.html` (keep the content, restyle less).

## 11. Not changing

The stack, the hosting, private mode, the Temporal design, the database schema beyond the new fields
(`scam`, `repeat_of`, `last_amount_inr`, notification kind `scam_warning`), and the four V1 hard
rules.
