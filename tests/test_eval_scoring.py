from eval.run_eval import latency, score_paper, score_scam, score_speech, silent_errors

MOTOR_TRUTH = {"category": "motor_insurance", "amount_inr": 18400, "due_date": "2026-12-14",
               "consequence_keywords": ["no claim bonus"], "scam_level": ["none"], "scam_signs": []}


def test_score_paper_counts_each_field():
    card = {"actions": [{"category": "motor_insurance", "amount_inr": 18400, "due_date": "2026-12-14",
                         "consequence": "No Claim Bonus lost", "needs_check": []}], "summary_hi": "यह बीमा है।"}
    assert score_paper(MOTOR_TRUTH, card) == {"category": True, "amount": True, "due": True, "consequence": True,
                                              "hindi": True}
    wrong = {"actions": [{**card["actions"][0], "amount_inr": 11775}], "summary_hi": "x"}
    s = score_paper(MOTOR_TRUTH, wrong)
    assert s["amount"] is False and s["hindi"] is False


def test_null_truth_wants_nothing_found_and_any_is_not_scored():
    truth = {"category": ["school_fee", "other"], "amount_inr": 500, "due_date": None, "consequence_keywords": [],
             "scam_level": ["none"], "scam_signs": []}
    card = {"summary_hi": "सूचना है", "actions": [{"category": "other", "amount_inr": 500, "due_date": None}]}
    assert score_paper(truth, card) == {"category": True, "amount": True, "due": True, "hindi": True}
    card["actions"][0]["due_date"] = "2026-10-15"     # an invented date is wrong
    assert score_paper(truth, card)["due"] is False
    scam_truth = {"category": "any", "amount_inr": "any", "due_date": "any", "consequence_keywords": [],
                  "scam_level": ["warning"], "scam_signs": ["asks_secret"]}
    assert score_paper(scam_truth, card) == {"hindi": True}


def test_wrong_but_highlighted_is_caught_not_correct():
    a = {"needs_check": ["amount_inr"]}
    assert silent_errors({"amount": False, "due": True}, a) == []
    assert silent_errors({"amount": True, "due": False}, a) == ["due"]
    assert silent_errors({"hindi": False}, a) == []


def test_scam_scoring_counts_false_alarms():
    card = {"scam": {"level": "warning", "signs": [{"sign": "personal_payment"}]}}
    scam = {"scam_level": ["warning"], "scam_signs": ["prize_refund", "personal_payment"]}
    assert score_scam(scam, card) == {"level_ok": True, "false_alarm": False, "signs_found": 1, "signs_expected": 2}
    genuine = {"scam_level": ["none", "caution"], "scam_signs": []}
    assert score_scam(genuine, card)["false_alarm"] is True
    assert score_scam(genuine, {"scam": {"level": "caution", "signs": []}}) == {
        "level_ok": True, "false_alarm": False, "signs_found": 0, "signs_expected": 0}
    assert score_scam(genuine, {})["level_ok"] is True     # a speech card has no scam field


def test_score_speech_matches_expected_actions():
    expect = [{"tool": "mark_done", "obligation_id": "ob_school"},
              {"tool": "snooze", "obligation_id": "ob_lic", "until": "2026-10-09"}]
    card = {"actions": [{"tool": "mark_done", "obligation_id": "ob_school"},
                        {"tool": "snooze", "obligation_id": "ob_lic", "until": "2026-10-09"}]}
    assert all(score_speech(expect, card).values())
    card["actions"][1]["until"] = "2026-10-16"
    assert not all(score_speech(expect, card).values())


def test_latency_reports_median_and_p90():
    assert latency([float(x) for x in range(1, 11)]) == (5.5, 9.0)


def test_a_two_part_question_may_be_answered_in_two_parts():
    expect = [{"tool": "answer", "used_obligation_ids": ["ob_elec"]}]
    card = {"actions": [{"tool": "answer", "used_obligation_ids": ["ob_elec"]},
                        {"tool": "answer", "used_obligation_ids": []}]}
    assert all(score_speech(expect, card).values())
    assert not all(score_speech(expect, {"actions": [{"tool": "answer", "used_obligation_ids": []},
                                                     {"tool": "answer", "used_obligation_ids": []}]}).values())
