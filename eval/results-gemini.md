# Eval — gemini:models/gemma-4-26b-a4b-it (2026-10-02 18:10)

Fictitious documents; photo conditions and voices are simulated (see eval/README).

- Paper fields exactly right: **40/40** (100%)
- Wrong amounts or dates that were NOT highlighted (silent errors): **0**
- Scam messages shown the red warning: **0/0**
- Genuine papers wrongly shown the red warning (false alarms): **0**
- Typed instructions fully right: **1/2**
- Spoken clips (synthetic voice + noise) fully right: **2/2**
- Time per call: median **10.6 s**, 90th percentile **12.2 s**

## Papers by photo condition (simulated)

| condition | fields right | silent errors |
|---|---|---|
| clean | 10/10 | 0 |
| tilted | 10/10 | 0 |
| dim | 10/10 | 0 |
| creased | 10/10 | 0 |

## Every photo

| document | condition | score | time | wrong | highlighted | scam level |
|---|---|---|---|---|---|---|
| motor_renewal | clean | 5/5 | 12.2s | — | — | none |
| motor_renewal | tilted | 5/5 | 10.6s | — | — | none |
| motor_renewal | dim | 5/5 | 10.9s | — | — | none |
| motor_renewal | creased | 5/5 | 10.7s | — | — | none |
| electricity_bill | clean | 5/5 | 10.7s | — | — | none |
| electricity_bill | tilted | 5/5 | 10.8s | — | — | none |
| electricity_bill | dim | 5/5 | 14.1s | — | — | none |
| electricity_bill | creased | 5/5 | 10.1s | — | — | none |

## Typed instructions

| case | score | time | wrong |
|---|---|---|---|
| new_insurance_hinglish | 4/4 | 4.6s | — |
| question_hindi | 1/2 | 4.4s | tools |

## Spoken clips (synthetic voice + noise)

| case | score | time | wrong |
|---|---|---|---|
| a_new_insurance | 4/4 | 6.8s | — — heard: यह गाड़ी के insurance का कागज़ आया है। premium 18,400 रुपए है और last date 14 दिसंबर है। मुझे एक हफ्ता पहले याद दिला देना और अगर मैं भूल जाऊं तो बेटे को बता देना। |
| a_done_and_snooze | 4/4 | 5.3s | — — heard: School की fees आज जमा कर दी। रसीद भी मिल गई और LIC वाला reminder Friday तक आगे कर दो। |
