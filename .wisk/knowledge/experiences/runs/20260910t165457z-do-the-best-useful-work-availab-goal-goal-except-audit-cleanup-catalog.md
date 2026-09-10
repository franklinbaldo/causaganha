---
goal: "Audit the remaining 'confirm-and-cite or narrow' except-Exception sites named by wiki paragraph 59's continuation: scripts/dev/cleanup_deprecated_ia_items.py (3 sites) and scripts/generate_catalog.py (4 sites), classifying each as a genuine per-item worker-pool bulkhead (cite docs/adr/0011) or a single-shot operation (narrow to specific exception types), extending tests/test_except_exception_policy.py to enforce it."
id: "run-goals/20260910t165457z-do-the-best-useful-work-availab/goal-except-audit-cleanup-catalog"
kind: "task-advance"
rationale: "These are the last two files in the except-Exception scoped-audit lineage still needing 'the full per-site read' per the wiki's own recorded next_move after PR #1427/#1428 (the other three files -- batch_embed_decisions.py, build_gold_benchmark.py, daily_benchmark_update.py -- already carry inline noqa:BLE001 reasoning and are a lighter confirm-and-cite pass, deferred to keep this round scoped to the two unread files)."
run: "runs/20260910T165457Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "tests/test_except_exception_policy.py enforces both files (cleanup_deprecated_ia_items.py fully cited via _SCRIPTS_CHECKED, generate_catalog.py fully narrowed via a new zero-bare-except-Exception assertion); full ruff+pytest green; PR opened."
type: "RunGoal"
---

# RunGoal
