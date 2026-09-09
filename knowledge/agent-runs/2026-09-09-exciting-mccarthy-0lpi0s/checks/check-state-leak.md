---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-0lpi0s-check-state-leak"
run_id: "2026-09-09-exciting-mccarthy-0lpi0s"
goal_id: "2026-09-09-exciting-mccarthy-0lpi0s-goal-fixture-network-guard"
command: "uv run pytest tests/test_render_contract_fixture.py tests/test_render_queries.py -q (run twice: before and after decision-unify-patch-restore's fix; git stash to confirm baseline on unmodified main)"
result: "failed"
evidence_id: "2026-09-09-exciting-mccarthy-0lpi0s-evidence-state-leak-repro"
summary: "Before the patch/restore unification: 2 failures in tests/test_render_queries.py when run after this round's new test file in the same session (confirmed absent on unmodified main via git stash -- a genuine regression, not a pre-existing flake). After applying _patched_attrs: same two-file run passes (51 passed)."
---

# Check: vazamento de estado entre arquivos de teste

Confirmada a regressão (ausente na `main` sem modificação) e sua correção via `_patched_attrs`.
