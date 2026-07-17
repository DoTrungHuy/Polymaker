from scripts.evaluate_gold import evaluate


def test_gold_scenario_top_three_hit_rate_is_at_least_80_percent():
    passed, total, failures = evaluate()
    assert passed / total >= 0.80, "\n".join(failures)
