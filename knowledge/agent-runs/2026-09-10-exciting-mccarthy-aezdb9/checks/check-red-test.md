---
type: AgentCheck
id: "2026-09-10-exciting-mccarthy-aezdb9-check-red-test"
run_id: "2026-09-10-exciting-mccarthy-aezdb9"
goal_id: "2026-09-10-exciting-mccarthy-aezdb9-goal-ia-rate-limit-fallback"
command: "uv run pytest tests/djen_backup/test_ia_rate_limit_parsing.py -q"
result: "failed"
evidence_id: "2026-09-10-exciting-mccarthy-aezdb9-evidence-red-test"
summary: "Expected failure before the fix: collection ImportError for the not-yet-existing _parse_ia_max_rate. Confirms the test is exercising new behavior, not an already-passing assertion."
---

# Check: RED antes do fix

`uv run pytest tests/djen_backup/test_ia_rate_limit_parsing.py -q` falha na coleta (ImportError) contra o `archive.py` sem a correção.
