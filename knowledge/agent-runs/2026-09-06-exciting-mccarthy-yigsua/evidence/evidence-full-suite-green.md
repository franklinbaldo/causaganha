---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-yigsua-evidence-full-suite-green"
run_id: "2026-09-06-exciting-mccarthy-yigsua"
goal_id: "2026-09-06-exciting-mccarthy-yigsua-goal-fix-1197-query-error-classification"
kind: "ci"
reference: "npx vitest run (web/, full suite); npx astro check (web/); uv run ruff check; uv run ruff format --check; uv run pytest -q"
summary: "Full web suite: 430/430 tests pass across 54 files (up from 424/53 before this round, matching the 6 new #1197 tests). astro check: 19 errors / 0 warnings / 5 hints, identical file-for-file to the pre-round baseline (confirmed via git stash on the .svelte change) — no new type errors from this round. ruff check: 'All checks passed!'; ruff format --check: '378 files already formatted' (no Python source changed; the regenerated domain_models.py/processoConsultar.gen.ts ended up byte-identical to committed, see evidence-generated-files-zero-diff). pytest -q: every test passes except test_check_agent_run_completeness.py's own-report-tree check, which is expected to fail until this run.md's completed_at/considered_work/selected_work/etc. are filled in just before the PR push, per the scaffold's documented contract."
---

# Evidência — suíte completa e gates verdes

Web: 430/430 testes, 54 arquivos. `astro check`: 19 erros pré-existentes, sem mudança. Python: `ruff check`/`ruff format --check` verdes, nenhum arquivo de produção alterado. `pytest -q`: única falha esperada é a completude do próprio relatório desta rodada, ainda em preenchimento.
