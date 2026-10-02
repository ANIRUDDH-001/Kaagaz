from ai.scam import check_signs, level, scam_summary


def test_signs_need_words_that_show_them():
    signs = check_signs([
        {"sign": "personal_payment", "evidence": "pay the fee to kbcprize.claim@ybl"},
        {"sign": "asks_secret", "evidence": "Pay at any cash counter"},        # no OTP/PIN in the words: dropped
        {"sign": "remote_app", "evidence": ""},                              # no words: dropped
        {"sign": "made_up", "evidence": "anything"},                         # not a sign we know: dropped
        {"sign": "personal_payment", "evidence": "or 9876543210@paytm"},     # same sign again: dropped
        "not even an object",
    ])
    assert [s["sign"] for s in signs] == ["personal_payment"]
    assert check_signs(None) == [] and check_signs("x") == []


def test_a_genuine_bills_helpline_and_website_never_make_a_red_warning():
    signs = check_signs([
        {"sign": "call_number", "evidence": "For complaints call 94250 12345"},
        {"sign": "suspicious_link", "evidence": "Pay online at www.mkvvn.in"},
        {"sign": "personal_payment", "evidence": "SMS your consumer number to 9425012345"},  # a number, no payment
        {"sign": "personal_payment", "evidence": "e-mail care@mkvvn.in"},                     # an e-mail, not UPI
        {"sign": "threat_deadline", "evidence": "supply may be disconnected 15 days after the due date"},
    ])
    assert {s["sign"] for s in signs} == {"call_number", "suspicious_link"}
    assert level(signs) == "caution"


def test_strong_signs_or_a_threat_with_a_number_make_a_warning():
    assert level(check_signs([{"sign": "suspicious_link", "evidence": "Update KYC: http://bit.ly/kyc-sbn-upd"}])) == "warning"
    assert level(check_signs([{"sign": "suspicious_link", "evidence": "Pay: https://echallan-parivahan.top/pay"}])) == "warning"
    both = [{"sign": "threat_deadline", "evidence": "will be disconnected tonight at 9.30 pm"},
            {"sign": "call_number", "evidence": "contact our electricity officer 98765 43210"}]
    assert level(check_signs(both)) == "warning"
    assert level(check_signs(both[:1])) == "caution"
    assert level([]) == "none"


def test_hindi_evidence_counts():
    signs = check_signs([
        {"sign": "threat_deadline", "evidence": "आज रात 8 बजे बंद कर दिया जाएगा"},
        {"sign": "remote_app", "evidence": "AnyDesk ऐप डाउनलोड करें"},
        {"sign": "personal_payment", "evidence": "₹1,520 इस UPI पर भेजें: gasseva.help@okaxis"},
        {"sign": "prize_refund", "evidence": "आपको ₹25,00,000 का इनाम मिला है"},
    ])
    assert {s["sign"] for s in signs} == {"threat_deadline", "remote_app", "personal_payment", "prize_refund"}


def test_long_evidence_is_checked_whole_then_cut_for_display():
    ev = "x" * 250 + " share the OTP"
    [s] = check_signs([{"sign": "asks_secret", "evidence": ev}])
    assert len(s["evidence"]) == 200


def test_summary_labels_every_sign_in_both_languages():
    summary = scam_summary(check_signs([{"sign": "asks_secret", "evidence": "Share the OTP you receive"}]))
    assert summary["level"] == "warning"
    assert summary["signs"][0]["en"] == "Asks for an OTP, PIN or password"
    assert summary["signs"][0]["hi"] == "OTP, PIN या पासवर्ड माँगता है"
