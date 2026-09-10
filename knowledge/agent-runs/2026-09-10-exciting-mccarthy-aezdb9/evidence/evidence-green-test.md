---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-aezdb9-evidence-green-test"
run_id: "2026-09-10-exciting-mccarthy-aezdb9"
goal_id: "2026-09-10-exciting-mccarthy-aezdb9-goal-ia-rate-limit-fallback"
kind: "test_green"
reference: "uv run pytest tests/djen_backup/test_ia_rate_limit_parsing.py -q and uv run pytest tests/djen_backup/ -q, run against archive.py after the fix"
summary: "The 5 new tests pass (5/5). Full tests/djen_backup/ package (131 tests, up from 126 after last round's addition) passes with no regressions -- the reorder from last round (goal-cb-probe-lock-order) and this round's parsing fix coexist cleanly."
---

# Evidência GREEN

```
$ uv run pytest tests/djen_backup/test_ia_rate_limit_parsing.py -q
.....                                                                    [100%]

$ uv run pytest tests/djen_backup/ -q
........................................................................ [ 55%]
.........................................................                [100%]
131 passed
```
