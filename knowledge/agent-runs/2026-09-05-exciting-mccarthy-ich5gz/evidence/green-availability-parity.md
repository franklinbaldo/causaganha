---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-ich5gz-evidence-green-availability-parity"
run_id: "2026-09-05-exciting-mccarthy-ich5gz"
goal_id: "2026-09-05-exciting-mccarthy-ich5gz-goal-fonte-indisponivel-vs-ausente-parity"
kind: "test_green"
reference: "git stash pop ; npx vitest run processoQueryPlanParity (web/); npx vitest run (web/, full suite); uv run pytest -q tests/causaganha/processos/"
summary: "After restoring the fixture (CNJ_SOURCE_UNAVAILABLE + missing_djen path in query_plan_fixtures.py), the manifest-writer exposing it (processo_query_plan_fixture.py), the safe-execution + avisos-exposing bridge (processo_query_plan_compare.py's _safe_rows and _python_mapped returning avisos), and the extracted formatFonteIndisponivelAviso() export in processoCnj.ts: processoQueryPlanParity.test.ts is 4/4 passing (up from 3/3 baseline). The new test proves, against the same shared fixture: raw SQL raises identically on both Python and Web engines for the broken djen parquet, and never raises for the merely-absent CNJ; the real _build_djen() mapper degrades the broken case to present:false plus exactly one aviso matching `Fonte 'djen' indisponível para este processo: ...`, while the absent case degrades to present:false with zero avisos; and the aviso's exception detail, round-tripped through formatFonteIndisponivelAviso('djen', detalhe), reproduces the exact string Python produced. Full web vitest suite: 358/358 passing (up from 357 at session start). Full uv run pytest -q tests/causaganha/processos/: 32/32 passing, unaffected by the additive fixture row."
---

# GREEN: prova de disponibilidade passa após a implementação

`processoQueryPlanParity.test.ts`: 4/4. Suite web completa: 358/358. `tests/causaganha/processos/`: 32/32. Nenhuma regressão nos testes pré-existentes que dependem da mesma fixture compartilhada.
