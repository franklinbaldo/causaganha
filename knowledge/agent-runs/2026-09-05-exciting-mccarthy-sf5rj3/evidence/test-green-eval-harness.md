---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-sf5rj3-evidence-test-green-eval-harness"
run_id: "2026-09-05-exciting-mccarthy-sf5rj3"
goal_id: "2026-09-05-exciting-mccarthy-sf5rj3-goal-close-1052-eval-harness-already-built"
kind: "test_green"
reference: "uv run pytest tests/segmenter_dataset/test_model_eval.py tests/segmenter_dataset/test_region_eval.py -q"
summary: "84 tests passed (45 in test_model_eval.py + 39 in test_region_eval.py), zero failures. Explicitly covers #1052's named acceptance-criteria edge cases: zero-support/zero-recall categories (test_critical_category_f1_covers_every_fixed_category_even_with_zero_support, test_micro_metrics_no_gold_or_predicted_spans_is_zero), and region reconstruction edge cases (test_compare_regions_missing_prediction_is_unmatched_not_zero_error, test_detect_inverted_regions_flags_fim_anchor_before_inicio_anchor, test_region_match_rate_empty_gold_is_none_not_zero)."
---

# Evidência — testes verdes do harness de avaliação

84/84 testes passando em `test_model_eval.py` + `test_region_eval.py`, cobrindo exatamente os edge cases que a #1052 exige nos critérios de aceite.
