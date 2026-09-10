---
goal: "Audit all 10 bare 'except Exception' sites in scripts/pipeline/consolidate.py (the largest remaining unaudited file in the except-Exception scoped-audit lineage, per wiki paragraph 59), classifying each as a genuine per-item worker-pool bulkhead (cite docs/adr/0011) or a single-shot non-loop operation (narrow to specific exception types), then extend tests/test_except_exception_policy.py to enforce it."
id: "run-goals/20260910t162621z-do-the-best-useful-work-availab/goal-consolidate-except-audit"
kind: "task-advance"
rationale: "Continues the lineage started by ADR-0011/PR #1289 and extended by PRs #1423/#1425: consolidate.py was explicitly named as the largest remaining file needing the full per-site read in run 20260910T153950Z's next_move. A separate audit of src/tcu_acordaos and src/causaganha_cli (this round's first candidate, per run 20260910T102506Z's still-open goal-audit-tcu-cli rationale) found both modules already fully read end-to-end with complete test coverage and no defect -- a dead end worth recording so a future round doesn't re-attempt it."
run: "runs/20260910T162621Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "tests/test_except_exception_policy.py's test_confirmed_scripts_bulkheads_cite_the_bulkhead_adr passes with scripts/pipeline/consolidate.py added to _SCRIPTS_CHECKED; the file's 6 genuine bulkhead sites cite docs/adr/0011 and its 4 single-shot sites are narrowed to specific exception types with zero bare except-Exception remaining uncited; full ruff+pytest green; PR opened."
type: "RunGoal"
---

# RunGoal
