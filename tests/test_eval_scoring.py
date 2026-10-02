from eval.run_eval import score_paper, score_speech, silent_errors


def test_score_paper_counts_each_field():
    card = {"actions": [{"category": "motor_insurance", "amount_inr": 18400, "due_date": "2026-12-14",
                         "consequence": "No Claim Bonus lost", "needs_check": []}], "summary_hi": "यह बीमा है।"}
    assert score_paper("motor_renewal", card) == {"category": True, "amount": True, "due": True,
                                                  "consequence": True, "hindi": True}
    wrong = {"actions": [{**card["actions"][0], "amount_inr": 11775, "needs_check": ["amount_inr"]}],
             "summary_hi": "x"}
    s = score_paper("motor_renewal", wrong)
    assert s["amount"] is False and s["hindi"] is False


def test_wrong_but_highlighted_is_caught_not_correct():
    a = {"needs_check": ["amount_inr"]}
    assert silent_errors({"amount": False, "due": True}, a) == []          # wrong, but highlighted
    assert silent_errors({"amount": True, "due": False}, a) == ["due"]     # wrong and not highlighted


def test_score_speech_matches_expected_actions():
    card = {"actions": [{"tool": "mark_done", "obligation_id": "ob_school"},
                        {"tool": "snooze", "obligation_id": "ob_lic", "until": "2026-10-09"}]}
    assert all(score_speech("done_and_snooze_hinglish", card).values())
    card["actions"][1]["until"] = "2026-10-16"
    assert not all(score_speech("done_and_snooze_hinglish", card).values())
