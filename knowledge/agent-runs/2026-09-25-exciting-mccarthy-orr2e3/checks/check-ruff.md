---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-orr2e3-check-ruff"
run_id: "2026-09-25-exciting-mccarthy-orr2e3"
goal_id: "2026-09-25-exciting-mccarthy-orr2e3-goal-tm02-stale-doc"
command: "uv run ruff check docs/SECURITY_THREAT_MODEL.md knowledge/backlog/issue-950.md knowledge/backlog/issue-951.md && uv run ruff format --check ."
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-orr2e3-evidence-tm02-diff"
summary: "Nenhum arquivo Python tocado nesta rodada (só Markdown); `ruff check` reportou 'warning: No Python files found' (esperado) e 'All checks passed!'. `ruff format --check .` sobre o repositório inteiro: 462 arquivos já formatados, 0 a reformatar."
---

# Check: ruff (lint + format) sobre o repositório inteiro
