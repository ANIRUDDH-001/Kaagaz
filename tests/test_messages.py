from datetime import date

from flows.messages import escalation_text, inr, reminder_text

OB = {"title": "Car insurance renewal", "title_hi": "गाड़ी का इंश्योरेंस", "amount_inr": 18400,
      "due_date": "2026-12-14"}


def test_inr_uses_indian_grouping():
    assert inr(18400) == "₹18,400"
    assert inr(123456) == "₹1,23,456"
    assert inr(950) == "₹950"
    assert inr(2346.0) == "₹2,346"
    assert inr(None) == ""


def test_reminder_text_real():
    hi, en = reminder_text(OB, "d7", date(2026, 12, 7), demo=False)
    assert hi == "गाड़ी का इंश्योरेंस, ₹18,400 — आख़िरी तारीख़ 14 दिसंबर, 7 दिन बचे हैं।"
    assert en == "Car insurance renewal, ₹18,400 — due 14 Dec 2026 (7 days left)."


def test_reminder_text_demo_says_which_reminder():
    hi, _ = reminder_text(OB, "d30", date(2026, 10, 2), demo=True)
    assert hi.startswith("(30 दिन पहले वाला reminder) ")


def test_reminder_text_due_tomorrow_and_overdue():
    assert "कल आख़िरी दिन है" in reminder_text(OB, "d1", date(2026, 12, 13), demo=False)[0]
    assert "2 दिन पहले निकल चुकी है" in reminder_text(OB, "now", date(2026, 12, 16), demo=False)[0]


def test_reminder_without_amount():
    hi, _ = reminder_text({**OB, "amount_inr": None}, "d7", date(2026, 12, 7), demo=False)
    assert hi.startswith("गाड़ी का इंश्योरेंस — आख़िरी तारीख़")


def test_escalation_text():
    hi, en = escalation_text(OB, date(2026, 12, 13))
    assert "पापा ने अभी तक गाड़ी का इंश्योरेंस" in hi
    assert en == "Papa hasn't marked Car insurance renewal (₹18,400, due 14 Dec) as done. Please check with him."
