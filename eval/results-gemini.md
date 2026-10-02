# Eval — gemini:models/gemma-4-26b-a4b-it (2026-10-02 18:38)

Fictitious documents; photo conditions and voices are simulated (see eval/README).

- Paper fields exactly right: **412/412** (100%)
- Wrong amounts or dates that were NOT highlighted (silent errors): **0**
- Scam messages shown the red warning: **24/24**
- Genuine papers wrongly shown the red warning (false alarms): **0**
- Typed instructions fully right: **20/20**
- Spoken clips (synthetic voice + noise) fully right: **8/8**
- Time per call: median **9.7 s**, 90th percentile **13.4 s**

## Papers by photo condition (simulated)

| condition | fields right | silent errors |
|---|---|---|
| clean | 103/103 | 0 |
| tilted | 103/103 | 0 |
| dim | 103/103 | 0 |
| creased | 103/103 | 0 |

## Every photo

| document | condition | score | time | wrong | highlighted | scam level |
|---|---|---|---|---|---|---|
| motor_renewal | clean | 5/5 | 15.2s | — | — | none |
| motor_renewal | tilted | 5/5 | 8.6s | — | — | none |
| motor_renewal | dim | 5/5 | 9.0s | — | — | none |
| motor_renewal | creased | 5/5 | 9.1s | — | — | none |
| electricity_bill | clean | 5/5 | 8.2s | — | — | none |
| electricity_bill | tilted | 5/5 | 9.1s | — | — | none |
| electricity_bill | dim | 5/5 | 7.9s | — | — | none |
| electricity_bill | creased | 5/5 | 8.4s | — | — | none |
| school_fee | clean | 5/5 | 14.3s | — | — | none |
| school_fee | tilted | 5/5 | 13.9s | — | — | none |
| school_fee | dim | 5/5 | 13.9s | — | — | none |
| school_fee | creased | 5/5 | 13.4s | — | — | none |
| property_tax | clean | 5/5 | 10.5s | — | — | none |
| property_tax | tilted | 5/5 | 8.8s | — | — | none |
| property_tax | dim | 5/5 | 11.2s | — | — | none |
| property_tax | creased | 5/5 | 11.7s | — | — | none |
| water_bill_hi | clean | 5/5 | 8.4s | — | — | none |
| water_bill_hi | tilted | 5/5 | 10.2s | — | — | none |
| water_bill_hi | dim | 5/5 | 11.2s | — | — | none |
| water_bill_hi | creased | 5/5 | 11.5s | — | — | none |
| gas_bill_en | clean | 5/5 | 12.1s | — | — | none |
| gas_bill_en | tilted | 5/5 | 11.1s | — | — | none |
| gas_bill_en | dim | 5/5 | 11.1s | — | — | none |
| gas_bill_en | creased | 5/5 | 9.8s | — | — | none |
| health_renewal | clean | 5/5 | 9.9s | — | — | none |
| health_renewal | tilted | 5/5 | 10.4s | — | — | none |
| health_renewal | dim | 5/5 | 9.5s | — | — | none |
| health_renewal | creased | 5/5 | 10.3s | — | — | none |
| life_premium | clean | 5/5 | 11.7s | — | — | none |
| life_premium | tilted | 5/5 | 12.1s | — | — | none |
| life_premium | dim | 5/5 | 11.9s | — | — | none |
| life_premium | creased | 5/5 | 9.6s | — | — | none |
| college_fee | clean | 5/5 | 9.3s | — | — | none |
| college_fee | tilted | 5/5 | 11.7s | — | — | none |
| college_fee | dim | 5/5 | 11.2s | — | — | none |
| college_fee | creased | 5/5 | 11.5s | — | — | none |
| dl_renewal | clean | 5/5 | 9.1s | — | — | none |
| dl_renewal | tilted | 5/5 | 9.7s | — | — | none |
| dl_renewal | dim | 5/5 | 10.9s | — | — | none |
| dl_renewal | creased | 5/5 | 9.7s | — | — | none |
| property_tax_hi | clean | 5/5 | 11.3s | — | — | none |
| property_tax_hi | tilted | 5/5 | 10.8s | — | — | none |
| property_tax_hi | dim | 5/5 | 8.7s | — | — | none |
| property_tax_hi | creased | 5/5 | 10.9s | — | — | none |
| electricity_multi_date | clean | 5/5 | 10.5s | — | — | none |
| electricity_multi_date | tilted | 5/5 | 9.8s | — | — | none |
| electricity_multi_date | dim | 5/5 | 22.4s | — | — | none |
| electricity_multi_date | creased | 5/5 | 10.0s | — | — | none |
| no_due_circular | clean | 4/4 | 8.8s | — | due_date | none |
| no_due_circular | tilted | 4/4 | 10.4s | — | due_date | none |
| no_due_circular | dim | 4/4 | 8.8s | — | due_date | none |
| no_due_circular | creased | 4/4 | 34.8s | — | due_date | none |
| paid_receipt | clean | 3/3 | 8.5s | — | due_date | none |
| paid_receipt | tilted | 3/3 | 8.3s | — | due_date | none |
| paid_receipt | dim | 3/3 | 9.5s | — | due_date | none |
| paid_receipt | creased | 3/3 | 9.5s | — | due_date | none |
| genuine_disconnection | clean | 5/5 | 11.2s | — | — | none |
| genuine_disconnection | tilted | 5/5 | 8.3s | — | — | none |
| genuine_disconnection | dim | 5/5 | 14.9s | — | — | none |
| genuine_disconnection | creased | 5/5 | 11.7s | — | — | none |
| two_wheeler | clean | 5/5 | 10.9s | — | — | none |
| two_wheeler | tilted | 5/5 | 8.5s | — | — | none |
| two_wheeler | dim | 5/5 | 11.5s | — | — | none |
| two_wheeler | creased | 5/5 | 9.1s | — | — | none |
| broadband | clean | 5/5 | 9.5s | — | — | none |
| broadband | tilted | 5/5 | 9.6s | — | — | none |
| broadband | dim | 5/5 | 10.1s | — | — | none |
| broadband | creased | 5/5 | 9.6s | — | — | none |
| society_maintenance | clean | 5/5 | 12.1s | — | — | none |
| society_maintenance | tilted | 5/5 | 9.1s | — | — | none |
| society_maintenance | dim | 5/5 | 9.0s | — | — | none |
| society_maintenance | creased | 5/5 | 38.6s | — | — | none |
| tuition_hi | clean | 5/5 | 10.5s | — | — | none |
| tuition_hi | tilted | 5/5 | 11.9s | — | — | none |
| tuition_hi | dim | 5/5 | 8.0s | — | — | none |
| tuition_hi | creased | 5/5 | 9.7s | — | — | none |
| puc_expiry | clean | 5/5 | 11.0s | — | — | none |
| puc_expiry | tilted | 5/5 | 9.7s | — | — | none |
| puc_expiry | dim | 5/5 | 9.8s | — | — | none |
| puc_expiry | creased | 5/5 | 7.4s | — | — | none |
| scam_sms_power_cut | clean | 1/1 | 11.7s | — | due_date | warning |
| scam_sms_power_cut | tilted | 1/1 | 9.9s | — | due_date | warning |
| scam_sms_power_cut | dim | 1/1 | 12.1s | — | due_date | warning |
| scam_sms_power_cut | creased | 1/1 | 9.5s | — | due_date | warning |
| scam_sms_kyc_link | clean | 1/1 | 11.9s | — | due_date | warning |
| scam_sms_kyc_link | tilted | 1/1 | 9.8s | — | due_date | warning |
| scam_sms_kyc_link | dim | 1/1 | 9.4s | — | due_date | warning |
| scam_sms_kyc_link | creased | 1/1 | 7.9s | — | due_date | warning |
| scam_sms_challan_link | clean | 1/1 | 8.5s | — | due_date | warning |
| scam_sms_challan_link | tilted | 1/1 | 26.7s | — | due_date | warning |
| scam_sms_challan_link | dim | 1/1 | 11.0s | — | due_date | warning |
| scam_sms_challan_link | creased | 1/1 | 25.8s | — | due_date | warning |
| scam_whatsapp_lottery | clean | 1/1 | 11.0s | — | due_date | warning |
| scam_whatsapp_lottery | tilted | 1/1 | 11.4s | — | due_date | warning |
| scam_whatsapp_lottery | dim | 1/1 | 11.2s | — | due_date | warning |
| scam_whatsapp_lottery | creased | 1/1 | 8.7s | — | due_date | warning |
| scam_sms_refund_otp | clean | 1/1 | 10.1s | — | due_date | warning |
| scam_sms_refund_otp | tilted | 1/1 | 9.5s | — | due_date | warning |
| scam_sms_refund_otp | dim | 1/1 | 9.5s | — | due_date | warning |
| scam_sms_refund_otp | creased | 1/1 | 8.3s | — | due_date | warning |
| scam_whatsapp_gas_hi | clean | 1/1 | 57.7s | — | due_date | warning |
| scam_whatsapp_gas_hi | tilted | 1/1 | 12.3s | — | due_date | warning |
| scam_whatsapp_gas_hi | dim | 1/1 | 11.1s | — | due_date | warning |
| scam_whatsapp_gas_hi | creased | 1/1 | 40.7s | — | due_date | warning |

## Typed instructions

| case | score | time | wrong |
|---|---|---|---|
| new_insurance_hinglish | 4/4 | 33.6s | — |
| question_hindi | 2/2 | 9.2s | — |
| done_and_snooze_hinglish | 4/4 | 3.2s | — |
| property_tax_english | 3/3 | 5.0s | — |
| done_electricity_hinglish | 2/2 | 1.6s | — |
| lic_new_amount_hinglish | 3/3 | 2.8s | — |
| school_new_date_hinglish | 3/3 | 2.7s | — |
| snooze_parson_hindi | 3/3 | 2.0s | — |
| snooze_monday_english | 3/3 | 2.5s | — |
| question_school_english | 2/2 | 2.4s | — |
| question_lic_hinglish | 2/2 | 3.4s | — |
| ambiguous_hinglish | 1/1 | 3.3s | — |
| new_water_hindi | 3/3 | 4.8s | — |
| new_health_english | 4/4 | 4.8s | — |
| new_gas_hinglish | 3/3 | 4.9s | — |
| new_society_english | 3/3 | 4.4s | — |
| done_two_hinglish | 2/2 | 2.7s | — |
| electricity_new_amount_english | 3/3 | 2.8s | — |
| snooze_tomorrow_hinglish | 3/3 | 2.4s | — |
| nonsense_hinglish | 1/1 | 2.6s | — |

## Spoken clips (synthetic voice + noise)

| case | score | time | wrong |
|---|---|---|---|
| a_new_insurance | 4/4 | 7.2s | — — heard: यह गाड़ी के insurance का कागज़ आया है। premium 18,400 रुपए है और last date 14 दिसंबर है। मुझे एक हफ्ता पहले याद दिला देना और अगर मैं भूल जाऊं तो बेटे को बता देना। |
| a_done_and_snooze | 4/4 | 4.9s | — — heard: स्कूल की फीस आज जमा कर दी। रसीद भी मिल गई और LIC वाला reminder Friday तक आगे कर दो। |
| a_property_tax | 3/3 | 6.2s | — — heard: The property tax notice came today. The amount is twelve thousand three hundred and fifty rupees. Pay before 31st March to get the five percent rebate |
| a_snooze_parson | 3/3 | 3.5s | — — heard: बिजली के बिल की याद परसों दिलाना |
| a_new_water | 3/3 | 6.2s | — — heard: मेरा पानी का bill ₹640 का है। 20 अक्टूबर तक भरना है। |
| a_new_health | 4/4 | 6.6s | — — heard: Health insurance premium is $23,650 due on the 5th of November. Remind me 10 days before |
| a_new_gas | 3/3 | 6.8s | — — heard: गैस का बिल ₹1214 का है। 12 तारीख तक भरना है। |
| a_done_two | 2/2 | 4.4s | — — heard: School fees भी दे दी और बिजली का bill भी भर दिया। |
