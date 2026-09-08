---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-5c2heq-evidence-green-test"
run_id: "2026-09-08-exciting-mccarthy-5c2heq"
goal_id: "2026-09-08-exciting-mccarthy-5c2heq-goal-calendar-json-status-vocabulary"
kind: "test_green"
reference: "tests/test_generate_cache_from_manifest.py::test_calendar_day_buckets_sum_to_total"
summary: "After adding _calendar_bucket() and the pending/unknown fields to generate_calendar_json() in scripts/generate_cache_from_manifest.py, uv run pytest tests/test_generate_cache_from_manifest.py -q passes: uploaded=1, pending=2, absent=1, unknown=1, sum==total==5, exactly as predicted by the goal's success_signal."
---

# Evidencia: teste GREEN

Apos adicionar `_calendar_bucket()` e os campos `pending`/`unknown`, o teste novo passa com os valores exatos previstos no `success_signal`.
