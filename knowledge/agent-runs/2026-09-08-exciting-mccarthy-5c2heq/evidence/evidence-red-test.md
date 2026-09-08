---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-5c2heq-evidence-red-test"
run_id: "2026-09-08-exciting-mccarthy-5c2heq"
goal_id: "2026-09-08-exciting-mccarthy-5c2heq-goal-calendar-json-status-vocabulary"
kind: "test_red"
reference: "tests/test_generate_cache_from_manifest.py::test_calendar_day_buckets_sum_to_total"
summary: "uv run pytest tests/test_generate_cache_from_manifest.py -q fails with KeyError: 'pending' at the day['pending'] == 2 assertion -- confirms generate_calendar_json's output today has no 'pending' key at all (only uploaded/absent/total), exactly as the goal's success_signal predicted."
---

# Evidencia: teste RED

`generate_calendar_json` nao expoe bucket `pending` hoje -- `KeyError: 'pending'` confirmado ao rodar o teste novo antes da correcao.
