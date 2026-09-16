---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-c4y4rc-check-okf-parser-final"
run_id: "2026-09-16-exciting-mccarthy-c4y4rc"
goal_id: "2026-09-16-exciting-mccarthy-c4y4rc-goal-per-split-floor-diagnosis"
command: "uv run ruff check .; uv run ruff format --check .; uv run pytest -q; uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "ruff check: All checks passed. ruff format --check: 446 files already formatted. uv run pytest -q: suite completa verde (nenhuma falha, nenhum erro), incluindo tests/test_check_agent_run_completeness.py e os dois testes de drift dos artefatos gerados (Zod schemas, domain models Python) apos regenera-los pela ultima vez sobre o bundle final desta rodada. okf-parser check: conformant=true, 0 diagnostics, concept_count=1729."
---

# Check final: suite completa + okf-parser antes do commit/push

Ultima verificacao antes de commitar e abrir a PR: bundle OKF conformante,
artefatos derivados (`web/src/lib/processoConsultar.gen.ts`,
`src/causaganha_mcp/_generated/domain_models.py`) regenerados e
sincronizados com o bundle final, suite completa e lint/format limpos.
