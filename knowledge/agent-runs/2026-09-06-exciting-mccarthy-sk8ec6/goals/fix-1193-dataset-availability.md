---
type: AgentGoal
id: "2026-09-06-exciting-mccarthy-sk8ec6-goal-fix-1193-dataset-availability"
run_id: "2026-09-06-exciting-mccarthy-sk8ec6"
goal: "Make DuckDBExplorer.svelte distinguish a genuinely absent Internet Archive dataset (404, or valid metadata with no Parquet files) from a transiently unavailable source (5xx, network failure, invalid/unexpected response), per issue #1193's acceptance criteria, with a dedicated 'unavailable' UI state, a retry action, no permanent caching of transient failures, and no loss of the user's current tribunal/year selection or typed SQL."
rationale: "Live reading of DuckDBExplorer.svelte confirmed the bug exactly as #1193 describes: a single try/catch around the Internet Archive metadata probe collapsed every failure mode into 'missing', cached permanently for the session, telling users a dataset doesn't exist when the real cause could be an Internet Archive outage. #1193 was filed by the repo owner the same day, marked 'READY para IMPLEMENTAÇÃO', is scoped to one file, gates issue #1132 from proceeding, and has eight testable acceptance criteria including an explicit test list — the strongest, most concretely TDD-shaped candidate available among this round's open issues."
success_signal: "A new focused test file encodes the contract (404 and no-parquet-metadata classify as 'missing'; 5xx, rejected fetch, and malformed JSON classify as 'unavailable' with a distinct message and a 'Tentar verificar novamente' button; a retry after a transient failure can reach 'ready'; tribunal/year selection survives an 'unavailable' classification) and is RED against the pre-fix component, then GREEN after the fix. The full existing web test suite (`npx vitest run`) stays green with no regressions. Python gates (`ruff check`, `ruff format --check`, `pytest -q`) stay green since no Python file changes. A PR containing only the DuckDBExplorer.svelte fix, its test file, and this round's OKF report is opened against main."
status: "achieved"
---

# Goal: corrigir a classificação ausente vs. indisponível na `#1193`

Fazer `DuckDBExplorer.svelte` distinguir ausência real do dataset (404, ou metadata válida sem Parquet) de indisponibilidade transitória da fonte (5xx, falha de rede, resposta inválida), com estado visual distinto, ação de retry, e sem cache permanente do erro transitório — seguindo à risca os critérios de aceite da `#1193`.
