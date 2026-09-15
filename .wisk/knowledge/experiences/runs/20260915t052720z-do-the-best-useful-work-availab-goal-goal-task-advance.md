---
goal: "Close issue #1470's remaining code-addressable acceptance criteria: (2) Bloom filter/encoding/compression/size inspection detail for the CNJ column, and (7) a per-file regeneration plan derived from each file's classification bucket."
id: "run-goals/20260915t052720z-do-the-best-useful-work-availab/goal-task-advance"
kind: "task-advance"
rationale: "These are the only two open items on #1470 that do not require IA write credentials (confirmed absent again this round); #1470 is part of the active #1468 parent initiative and the audit script (scripts/audit_cnj_parquets.py) already has the classification machinery this builds on."
run: "runs/20260915T052720Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "scripts/audit_cnj_parquets.py's FooterStats/report gains cnj_column_details (type/compression/encodings/sizes/bloom) and regeneration_plan fields, backed by new RED-then-GREEN tests in tests/test_audit_cnj_parquets.py, full pytest/ruff green, and a merged PR closing the two criteria on #1470."
type: "RunGoal"
---

# RunGoal
