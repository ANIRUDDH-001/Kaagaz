# Eval — ollama:gemma4:e4b (2026-10-02 15:08)

> Earlier eval set (v1): 4 clean papers and 4 spoken instructions. The v2 run (26 documents × 4 conditions) on this laptop model was not completed for this submission.

**ollama:gemma4:e4b**: paper fields exactly right 18/20; wrong amounts/dates NOT highlighted (silent errors) 1/8; papers with a highlighted field 1/4; spoken instructions fully right 3/4

| kind | case | score | time | wrong | highlighted for checking |
|---|---|---|---|---|---|
| paper | electricity_bill | 4/5 | 16.8s | amount | — |
| paper | motor_renewal | 5/5 | 15.1s | — | — |
| paper | property_tax | 4/5 | 14.6s | due | due_date |
| paper | school_fee | 5/5 | 18.0s | — | — |
| speech | new_insurance_hinglish | 3/4 | 10.6s | create_obligation.amount_inr | — |
| speech | question_hindi | 2/2 | 5.8s | — | — |
| speech | done_and_snooze_hinglish | 4/4 | 4.1s | — | — |
| speech | property_tax_english | 3/3 | 7.9s | — | — |
