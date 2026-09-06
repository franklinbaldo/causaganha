---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-589obm-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-589obm"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "This round's selected work touches knowledge/okf.schema.sql, tests/knowledge/test_backlog.py, and knowledge/backlog/issue-985.md — none of djen_backup's manifest/DJEN-status rules or the .qmd query-contract pipeline apply. The relevant CLAUDE.md rule is the general correctness discipline it repeats for djen_raw/HTTP status ('a 403 is not proof of absence; verify against the live source before trusting a recorded status') applied by analogy to this round's own live network investigation of cdn.tse.jus.br for issue #985: a bare HTTP 403 there is Akamai's own 'Access Denied' page (network/WAF-level), not evidence the TSE dataset itself is unavailable, so the backlog record must describe it precisely rather than reuse an unrelated template reason. 'Before committing' gates apply repo-wide: uv run ruff check, uv run ruff format --check, uv run pytest -q — run and green before this report's completed_at is set."
---

# Leitura de CLAUDE.md

O trabalho desta rodada é só `knowledge/` (schema OKF + teste de backlog + um `BacklogItem`), sem tocar `djen_backup`/contratos `.qmd`. A analogia útil do CLAUDE.md é a regra de não tratar HTTP 403 como prova de ausência sem verificar a fonte viva — a mesma disciplina se aplica à checagem de rede feita nesta rodada contra `cdn.tse.jus.br` para a #985. Gates de commit: `ruff check`/`format --check`/`pytest -q`.
