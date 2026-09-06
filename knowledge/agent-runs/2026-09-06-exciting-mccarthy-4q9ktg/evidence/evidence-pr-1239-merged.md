---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-4q9ktg-evidence-pr-1239-merged"
run_id: "2026-09-06-exciting-mccarthy-4q9ktg"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1239"
summary: "PR #1239 (closing #1238) merged into main as commit 970235bc7de9707cdacec880758132ca92cf9c13 via squash merge. All 10 check runs were green before merge: lint, tests (tjro), web, validate, GitGuardian Security Checks, and CodeQL (python/actions/go/javascript-typescript) — mergeable_state reached 'clean'. Independently re-verified locally after review (not just trusted from CI): `uv run ruff check` / `uv run ruff format --check` on the 4 changed source/test files, `uv run pytest -q tests/causaganha/decisoes/test_published.py tests/causaganha_mcp/test_decisoes_buscar.py` (25/25 passed), and `uv run okf-parser check knowledge --relational-schema okf.schema.sql` (conformant, 0 diagnostics) before deciding to merge."
---

# Evidência: PR #1239 mesclada

`https://github.com/franklinbaldo/causaganha/pull/1239` mesclada em `main` como `970235b`, fechando `#1238`. 10/10 checks verdes antes do merge. Reverifiquei localmente (não só confiando na CI): ruff check/format nos arquivos alterados, `pytest -q` nos dois arquivos de teste novos/alterados (25/25), e `okf-parser check` conformante.
