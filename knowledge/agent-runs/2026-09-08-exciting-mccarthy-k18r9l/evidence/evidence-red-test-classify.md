---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-k18r9l-evidence-red-test-classify"
run_id: "2026-09-08-exciting-mccarthy-k18r9l"
goal_id: "2026-09-08-exciting-mccarthy-k18r9l-goal-classify-200-prefix-false-drift"
kind: "test_red"
reference: "uv run pytest -q tests/test_backfill_probe_classify.py (before the _classify() fix)"
summary: "Failed with: AssertionError: assert 'other:200:https://example.test/djen.zip' == 'available' for test_classify_available_on_200_with_detail_suffix. Confirms the '200:<detail>' djen_raw format falls into a mismatched bucket before the fix."
---

# Evidence: RED

Teste falhou antes do fix: `_classify("200:https://example.test/djen.zip")` retornava `"other:200:https://example.test/djen.zip"` em vez de `"available"`.
