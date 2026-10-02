from datetime import date

from ai.understand import (amount_supported, date_supported, plan_speech, read_paper, readback,
                           validate_create)
from tests.fakes import FakeGemma

TODAY = date(2026, 10, 2)
MOTOR = {"category": "motor_insurance", "issuer": "Suraksha General Insurance",
         "title": "Car insurance renewal", "title_hi": "गाड़ी का इंश्योरेंस", "amount_inr": 18400,
         "due_date": "2026-12-14", "action": "Renew the policy", "consequence": "No Claim Bonus is lost",
         "evidence_amount": "Total Premium Payable: ₹ 18,400", "evidence_due_date": "Policy expires on 14/12/2026",
         "evidence_consequence": "the No Claim Bonus will lapse", "summary_hi": "यह गाड़ी के बीमा का नोटिस है।"}
OBS = [
    {"_id": "ob_school", "title": "School fee", "title_hi": "स्कूल की फ़ीस", "amount_inr": 14500,
     "due_date": "2026-10-15", "status": "active"},
    {"_id": "ob_lic", "title": "LIC premium", "title_hi": "LIC प्रीमियम", "amount_inr": 9800,
     "due_date": "2026-10-20", "status": "active"},
]


async def test_clean_paper_needs_no_check_and_reads_back():
    card = await read_paper(FakeGemma(MOTOR), b"img", "image/jpeg", TODAY)
    a = card["actions"][0]
    assert a["tool"] == "create_obligation" and a["source"] == "photo"
    assert a["needs_check"] == [] and a["consequence"] == "No Claim Bonus is lost"
    assert a["remind_offsets_days"] == [30, 7, 1] and a["escalate"] is True
    assert card["readback_hi"] == "गाड़ी का इंश्योरेंस, ₹18,400, आख़िरी तारीख़ 14 दिसंबर। सही है?"
    assert card["summary_hi"] == "यह गाड़ी के बीमा का नोटिस है।"


async def test_computed_discount_is_flagged():
    raw = {**MOTOR, "amount_inr": 11775, "evidence_amount": "Total Demand ₹ 12,350"}
    card = await read_paper(FakeGemma(raw), b"img", "image/jpeg", TODAY)
    assert card["actions"][0]["needs_check"] == ["amount_inr"]


async def test_invented_date_is_flagged():
    raw = {**MOTOR, "due_date": "2026-10-31", "evidence_due_date": "paid on or before 31-03-2027"}
    assert (await read_paper(FakeGemma(raw), b"img", "image/jpeg", TODAY))["actions"][0]["needs_check"] == ["due_date"]


async def test_missing_date_stays_null():
    raw = {**MOTOR, "due_date": None, "evidence_due_date": None}
    card = await read_paper(FakeGemma(raw), b"img", "image/jpeg", TODAY)
    assert card["actions"][0]["due_date"] is None and "due_date" in card["actions"][0]["needs_check"]
    assert "तारीख़" not in card["readback_hi"]


async def test_consequence_without_evidence_is_dropped():
    raw = {**MOTOR, "consequence": "Vehicle may be seized", "evidence_consequence": None}
    assert (await read_paper(FakeGemma(raw), b"img", "image/jpeg", TODAY))["actions"][0]["consequence"] is None


def test_evidence_helpers():
    assert amount_supported(18400, "₹ 18,400.00")
    assert amount_supported(18400, "कुल राशि ₹ १८,४००")
    assert not amount_supported(11775, "Total Demand ₹ 12,350")
    assert date_supported(date(2026, 12, 14), "expires on 14/12/2026")
    assert date_supported(date(2026, 10, 15), "Last date: 15 Oct 2026")
    assert date_supported(date(2026, 12, 14), "अंतिम तिथि 14 दिसंबर")
    assert not date_supported(date(2026, 10, 31), "31-03-2027")


def test_date_supported_rejects_wrong_year():
    assert not date_supported(date(2026, 12, 14), "valid till 14/12/2027")
    assert not date_supported(date(2026, 12, 14), "१४ दिसंबर २०२७")
    assert date_supported(date(2026, 12, 14), "period 15/12/2025 to 14/12/2026")
    assert date_supported(date(2026, 12, 14), "14 Dec")          # no year printed: day and month decide


async def test_voice_create_with_week_reminder_and_son():
    plan = {"actions": [{"tool": "create_obligation", "title": "Car insurance", "title_hi": "गाड़ी का इंश्योरेंस",
                         "category": "motor_insurance", "amount_inr": 18400, "due_date": "2026-12-14",
                         "action": "Renew", "evidence": "atharah hazaar chaar sau, chaudah December",
                         "remind_before_days": 7, "escalate": False}]}
    card = await plan_speech(FakeGemma(plan), "...", OBS, TODAY)
    a = card["actions"][0]
    assert a["remind_offsets_days"] == [7, 1] and a["escalate"] is True and a["needs_check"] == []
    assert card["transcript"] == "..."


async def test_done_and_snooze_on_known_items():
    plan = {"actions": [{"tool": "mark_done", "obligation_id": "ob_school"},
                        {"tool": "snooze", "obligation_id": "ob_lic", "until": "2026-10-09"}]}
    card = await plan_speech(FakeGemma(plan), "...", OBS, TODAY)
    assert [a["tool"] for a in card["actions"]] == ["mark_done", "snooze"]
    assert card["readback_hi"] == "स्कूल की फ़ीस — हो गया। LIC प्रीमियम — 9 अक्टूबर को फिर याद दिलाऊँगा। सही है?"


async def test_unknown_item_or_past_snooze_becomes_clarify():
    plan = {"actions": [{"tool": "snooze", "obligation_id": "nope", "until": "2026-10-09"},
                        {"tool": "snooze", "obligation_id": "ob_lic", "until": "2026-09-01"}]}
    card = await plan_speech(FakeGemma(plan), "...", OBS, TODAY)
    assert [a["tool"] for a in card["actions"]] == ["clarify", "clarify"]
    assert "सही है?" not in card["readback_hi"]


async def test_answer_is_spoken_without_confirmation():
    plan = {"actions": [{"tool": "answer", "text_hi": "बिजली का बिल 10 अक्टूबर तक भरना है।",
                         "obligation_id": "ob_school"}]}
    card = await plan_speech(FakeGemma(plan), "...", OBS, TODAY)
    assert card["readback_hi"] == "बिजली का बिल 10 अक्टूबर तक भरना है।"
    assert card["actions"][0]["used_obligation_ids"] == ["ob_school"]


async def test_nothing_understood_asks_again():
    card = await plan_speech(FakeGemma({"actions": []}), "...", OBS, TODAY)
    assert card["actions"] == [{"tool": "clarify", "question_hi": "माफ़ कीजिए, समझ नहीं पाया। फिर से बोलिए।"}]


async def test_plan_prompt_carries_today_and_items():
    g = FakeGemma({"actions": []})
    await plan_speech(g, "LIC wala reminder Friday tak aage kar do", OBS, TODAY)
    assert "2026-10-02 (Friday)" in g.calls[0] and '"id": "ob_lic"' in g.calls[0]
    assert "LIC wala reminder Friday tak aage kar do" in g.calls[0]


def test_confirm_keeps_user_choices():
    a = validate_create({"tool": "create_obligation", "title": "X", "due_date": "2026-12-14", "amount_inr": 5,
                         "remind_offsets_days": [7, 1], "escalate": False, "source": "voice"}, TODAY, "confirm")
    assert a["remind_offsets_days"] == [7, 1] and a["escalate"] is False and a["source"] == "voice"


def test_readback_for_update():
    assert readback([{"tool": "update_obligation", "title_hi": "LIC प्रीमियम", "amount_inr": 9900,
                      "due_date": None}]) == "LIC प्रीमियम — नई रकम ₹9,900। सही है?"


def test_plan_schema_requires_every_field():
    # Ollama decodes against the schema: an optional field is one a small model may skip. E4B left out
    # amount_inr and due_date for a spoken new item until every field was required (nullable).
    from ai.prompts import PLAN_SCHEMA
    item = PLAN_SCHEMA["properties"]["actions"]["items"]
    assert set(item["required"]) == set(item["properties"])
