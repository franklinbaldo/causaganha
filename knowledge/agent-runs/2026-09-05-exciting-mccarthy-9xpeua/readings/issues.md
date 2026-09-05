---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-9xpeua-reading-issues"
run_id: "2026-09-05-exciting-mccarthy-9xpeua"
subject: "open_issues"
reference: "franklinbaldo/causaganha open issues (list_issues, state=OPEN, 32 total, checked 2026-09-05)"
finding: "No PR closes any open issue yet (closed_by_pull_requests empty on every one checked). #1105 (contract(product): projeção ProcessoConsultar OKF) closed 2026-09-05 as completed, which unblocks #1107 (contract(processo): eliminar drift do plano de consulta MCP/Web) into READY state, but #1107 is a multi-slice fixture-and-parity effort (Parquet fixtures for 4 sources + DuckDB/Python parity harness) too large for a single round. #1042 (ops(catalog): provar update-catalog ponta a ponta) requires observing a real IA-uploading GitHub Actions run — live/operational, not something to trigger unreviewed from an autonomous session. The web/UX backlog #1128-#1139 is READY, self-contained, client-side-only work with deterministic-test acceptance criteria. #1135 (web(proveniencia): oferecer ação consistente de copiar referência verificável) is scoped tightly enough for one TDD slice: a pure-function reference-text builder plus a button on ProcessoLookup.svelte, no backend/schema changes, acceptance criteria explicitly requires deterministic tests for the text format. Selected as this round's primary goal."
---

# Leitura de issues abertas

Levantamento do backlog aberto via `list_issues` (owner/repo `franklinbaldo/causaganha`). Não há PR aberto retomável nesta rodada (ver `AgentReading` sobre PRs) — a rodada precisa escolher trabalho novo do backlog. #1135 foi escolhida por ser self-contained, sem side effects externos, e already matching o padrão RED->GREEN da issue (critérios de aceite pedem "formato tem testes determinísticos").
