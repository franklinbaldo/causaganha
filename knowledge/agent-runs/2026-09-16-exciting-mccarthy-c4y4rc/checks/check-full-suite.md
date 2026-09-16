---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-c4y4rc-check-full-suite"
run_id: "2026-09-16-exciting-mccarthy-c4y4rc"
goal_id: "2026-09-16-exciting-mccarthy-c4y4rc-goal-per-split-floor-diagnosis"
command: "uv run ruff check .; uv run ruff format --check .; uv run pytest -q"
result: "passed"
evidence_id: "2026-09-16-exciting-mccarthy-c4y4rc-evidence-green-test"
summary: "ruff check: All checks passed. ruff format --check: 446 files already formatted. uv run pytest -q: suite completa verde apos regenerar web/src/lib/processoConsultar.gen.ts e src/causaganha_mcp/_generated/domain_models.py (drift esperado enquanto run.md estava em rascunho, ja documentado no proprio scaffold) e corrigir os nomes de campo do schema AgentCheck/AgentEvidence (command/result/kind) nos arquivos desta propria rodada."
---

# Check: suite completa apos o incremento de dominio e o fechamento do relatorio

Rodado apos: (1) implementar e testar a extensao de
`scripts/segmenter_governance_status.py`; (2) corrigir
`knowledge/backlog/issue-1050.md`/remover `issue-1051.md`; (3) preencher
`completed_at`/`result_summary`/`next_move` do `run.md` desta rodada; (4)
regenerar os dois artefatos derivados do bundle OKF
(`web/src/lib/processoConsultar.gen.ts`,
`src/causaganha_mcp/_generated/domain_models.py`). A primeira execucao da
suite completa (antes desta correcao) apontou 2 erros reais de schema nos
proprios arquivos `AgentCheck`/`AgentEvidence` desta rodada (`procedure`
nao declarado, `kind`/`result` fora do enum) via
`scripts/check_agent_run_completeness.py` -- corrigidos, e a suite
completa voltou a verde.
