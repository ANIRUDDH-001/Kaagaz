# Kaagaz eval

How well does Gemma 4 read household papers, catch scam messages, and follow spoken instructions?
`run_eval.py` answers with numbers, on any backend.

## What is in the set

- **26 documents** (`papers/*.html`, ground truth in `ground_truth.json`):
  - 20 genuine papers: electricity, water, gas and broadband bills, insurance renewals and premium notices, school
    and college fees, property tax, a driving licence and a PUC renewal, a society maintenance bill, a school circular
    with no due date, a payment receipt (nothing to pay), and a genuine disconnection notice;
  - 6 scam messages as SMS or WhatsApp screenshots: a "power cut tonight, call this number" SMS, a KYC link, a fake
    e-challan link, a lottery asking for a UPI payment, a "bonus refund" asking for an OTP, and a Hindi gas-connection
    threat asking for UPI and AnyDesk.
- **4 photo conditions** per document (`photos/<doc>__<condition>.jpg`): clean; tilted on a table with a shadow;
  dim warm light with sensor noise and heavy JPEG; creased, slightly rotated and blurred.
- **20 typed instructions** in Hindi, Hinglish and English: new papers, done, "remind me later", changed amounts and
  dates, questions, and ambiguous or nonsense input that should get a question back.
- **8 spoken clips** (`audio/*.wav`): 8 of those instructions read by two ElevenLabs voices, mixed with room noise and
  mains hum at 15 dB SNR, then sent through speech to text and Gemma.

## What is fictitious, what is simulated

Every name, number, organisation and link is invented; phone numbers use the 98765 dummy pattern; every document
says SPECIMEN. The photo conditions are made in code (`conditions.py`), and the voices are synthetic. They test the
pipeline under stress; they are not real phone photos or real elderly voices, and the results say so.

## Metrics

- **Paper fields exactly right:** category, amount (within ₹1), due date (exact), consequence (a keyword match), and
  a Hindi summary present. A field marked `"any"` in the truth is not scored (scam messages); `null` means nothing
  should be found, so an invented date counts as wrong.
- **Silent errors:** a wrong amount or date that the card did *not* highlight for checking. These are the errors that
  could be saved unnoticed, so this is the number that matters most.
- **Scam messages given the red warning:** scam documents whose card shows level `warning`.
- **False alarms:** genuine papers shown the red warning. Caution (amber) on the genuine disconnection notice is
  allowed; red is not.
- **Instructions fully right:** every expected action, with the right paper, amount, date or snooze day. A two-part
  question may be answered in two parts.
- **Time per call:** median and 90th percentile, one call per photo or instruction, including retries.

## Rerun it

```bash
pip install -r requirements-eval.txt
python -m eval.make_docs        # writes papers/*.html and the papers section of ground_truth.json
python -m eval.render_docs      # headless Edge -> renders/*.png -> photos/<doc>__<condition>.jpg
python -m eval.make_audio --voices SAz9YHcvj6GT2YYXdXww,XrExE9yKIg1WjnnlVkGX   # needs ELEVENLABS_API_KEY
python -m eval.run_eval                         # backend from .env; writes results-<backend>.md
python -m eval.run_eval --only papers --subset 6 # a quick look
```

For the laptop model: `LLM_BACKEND=ollama STT_BACKEND=whisper python -m eval.run_eval`.
