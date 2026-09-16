---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-hv2ep2-check-full-suite-red"
run_id: "2026-09-16-exciting-mccarthy-hv2ep2"
goal_id: "2026-09-16-exciting-mccarthy-hv2ep2-goal-batch9-corpus-growth"
evidence_id: "2026-09-16-exciting-mccarthy-hv2ep2-evidence-red-before-ingestion"
command: "uv run pytest -q"
result: "failed"
summary: "Full suite run after ingestion + new/edited tests but BEFORE this run.md existed: 1 failure, tests/knowledge/test_backlog.py::test_every_backlog_item_last_verified_run_id_resolves_to_a_real_round, because knowledge/backlog/issue-1050.md's last_verified_run_id already pointed at this round's id before knowledge/agent-runs/2026-09-16-exciting-mccarthy-hv2ep2/run.md existed. Expected and resolved by writing run.md next (see check-full-suite-green)."
---

# Check: suíte completa antes do run.md existir

Falha esperada e documentada pelo próprio scaffold
(`.claude/agent-run-scaffold.md`): o backlog já aponta
`last_verified_run_id` para esta rodada antes do `run.md` existir.
Resolvido escrevendo este relatório.
