---
type: AgentRun
id: "2026-09-05-exciting-mccarthy-e9r0mj"
started_at: "2026-09-05T18:10:00Z"
completed_at: "2026-09-05T18:55:00Z"
branch_at_start: "claude/exciting-mccarthy-e9r0mj"
commit_at_start: "916f63c2d875d6fc763c8234ce331496e068d0ef"
claude_md_reading_id: "2026-09-05-exciting-mccarthy-e9r0mj-reading-claude-md"
issues_reading_id: "2026-09-05-exciting-mccarthy-e9r0mj-reading-issues"
prs_reading_id: "2026-09-05-exciting-mccarthy-e9r0mj-reading-prs"
okf_reading_id: "2026-09-05-exciting-mccarthy-e9r0mj-reading-okf"
goal_ids: ["2026-09-05-exciting-mccarthy-e9r0mj-goal-datajud-temporal-authority"]
primary_goal_id: "2026-09-05-exciting-mccarthy-e9r0mj-goal-datajud-temporal-authority"
considered_work:
  - "Pick up #1107's queued 'DataJud temporal authority' fix — already root-caused by a prior closed-unmerged PR (#1125), single concrete file/function, clear regression test to write first"
  - "Pick a fresh but less concretely scoped web/UX issue (#1131-#1134, #1136) — no freshly-unblocked dependency this round"
  - "Re-check #950/#951 (MCP remote endpoint) now that the MCP stack (#1152) merged — plausible but a bigger, less TDD-shaped operational slice; deferred"
  - "#1042 (ops(catalog) end-to-end) — needs live IA-upload side effects, not reproducible autonomously"
selected_work: "Fix web/src/lib/processoCnj.ts's mapDatajudRow() to stop truncating DatajudCapa.ultima_atualizacao to a bare date via toIsoDate(); add a timestamp-preserving mapper and a regression test; then reintroduce the mapping-layer PRESENT/ABSENT parity proof across DJEN/JURIS/STJ/DataJud that PR #1125 attempted and correctly left unmerged."
expected_behavior: "mapDatajudRow({..., ultima_atualizacao: '2024-06-01 14:23:05'}).ultimaAtualizacao preserves the full instant ('2024-06-01T14:23:05'), matching Python service.py's _iso()/isoformat() semantics for the same DuckDB TIMESTAMP value, instead of truncating to '2024-06-01'. A bare DATE-typed value ('2024-06-01') still round-trips unchanged. A new mapping-layer parity test drives the real Python _build_datajud (via query_plan_fixtures.py's shared fixture) and the real Web mapDatajudRow/buscarProcesso against the same fixture rows and asserts the normalized dossier core agrees for both a DataJud-present and a DataJud-absent CNJ."
entry_state: "new"
target_state: "merged"
decision_ids:
  - "2026-09-05-exciting-mccarthy-e9r0mj-decision-timestamp-string-normalization"
  - "2026-09-05-exciting-mccarthy-e9r0mj-decision-reuse-1125-harness"
evidence_ids:
  - "2026-09-05-exciting-mccarthy-e9r0mj-evidence-red-timestamp-truncation"
  - "2026-09-05-exciting-mccarthy-e9r0mj-evidence-green-timestamp-fix"
  - "2026-09-05-exciting-mccarthy-e9r0mj-evidence-red-mapping-parity"
  - "2026-09-05-exciting-mccarthy-e9r0mj-evidence-green-mapping-parity"
  - "2026-09-05-exciting-mccarthy-e9r0mj-evidence-pr-1157"
check_ids:
  - "2026-09-05-exciting-mccarthy-e9r0mj-check-vitest-red-timestamp"
  - "2026-09-05-exciting-mccarthy-e9r0mj-check-vitest-green-timestamp"
  - "2026-09-05-exciting-mccarthy-e9r0mj-check-vitest-red-mapping-parity"
  - "2026-09-05-exciting-mccarthy-e9r0mj-check-vitest-green-mapping-parity"
  - "2026-09-05-exciting-mccarthy-e9r0mj-check-full-suite"
result_state: "review"
result_summary: "Fixed issue #1107's diagnosed DataJud temporal-authority drift end-to-end via 2 TDD slices, each RED-then-GREEN: (1) added toIsoTimestamp() to web/src/lib/processoCnj.ts — a syntactic (non-Date-reparsing) normalizer that preserves DatajudCapa.ultima_atualizacao's full instant instead of truncating it to a bare date via toIsoDate(), matching Python service.py's _iso()/datetime.isoformat() semantics for the same DuckDB TIMESTAMP column; wired it into mapDatajudRow(), with a new regression test proving time-of-day preservation, bare-date passthrough, and null passthrough; (2) reintroduced PR #1125's mapping-layer PRESENT/ABSENT parity test (scripts/processo_query_plan_compare.py's _python_mapped() dispatching to the real _build_djen/_build_juris/_build_stj/_build_datajud, plus the corresponding Vitest assertion in processoQueryPlanParity.test.ts), reused verbatim from the closed-unmerged PR since its design was already correct — it was closed specifically because it caught this exact drift. Manually verified both new tests go RED against the pre-fix code (confirmed by temporarily reverting mapDatajudRow and re-running) and GREEN after restoring the fix. Full web vitest suite: 357/357 passing (up from 356). eslint clean. astro typecheck: 19/0/3, identical to the pre-round baseline. ruff check/format --check: clean. uv run pytest -q: only the expected, self-resolving failure in test_check_agent_run_completeness.py (this round's own run.md was still missing completed_at/decision_ids/etc. at that point in the round, before this commit) — every other Python test passes, including tests/causaganha/processos/ (32/32). An incidental, unrelated web/src/lib/djen-zod.gen.ts regeneration drift from `npm ci` installing a newer pinned orval than the committed codegen output was reverted before committing. PR opened against main; see next_move for CI/merge follow-up."
next_move: "Watch this round's PR's CI to green, then merge it, closing the 'DataJud temporal authority' + 'mapping parity restoration' items of #1107's queued next-steps list. #1107 itself stays open after this merges — its remaining queued items (comment 5551321571) are: (3) prove 'fonte registrada mas parquet indisponível' distinct from 'CNJ ausente' across both runtimes; (4) prove documentos_truncados (MCP) / pagination (Web) observable equivalence, including stable ordering. Only after those should #1107 evaluate whether any SQL-plan duplication is mechanical enough to justify declarative generation — no DSL before a concrete divergence justifies it, per the issue's own repeated caution. A future round could also revisit #950/#951 (MCP remote HTTP endpoint) now that the MCP routing stack (#1152) is merged, or the still-open, less-scoped web/UX issues (#1131-#1134, #1136)."
---

# Agent run — 2026-09-05-exciting-mccarthy-e9r0mj

Rodada do loop horário do CausaGanha, orientada pelo scaffold `.claude/agent-run-scaffold.md`.

## O que aconteceu

1. **Leituras** (`readings/`): `CLAUDE.md`, issues abertas (29, #1107 READY com causa raiz já diagnosticada via PR #1125 fechada sem merge), PRs (0 abertas — branch de trabalho já mesclado em `main`) e conhecimento OKF (`DatajudCapa.ultima_atualizacao` é a única coluna genuinamente `TIMESTAMP` do dossiê; as demais datas são `DATE`).
2. **Continuidade escolhida**: issue #1107, passo "DataJud temporal authority" — já apontado pelo próprio autor como o próximo READY, com causa raiz identificada por uma PR anterior (#1125) que ficou corretamente vermelha.
3. **Fatia 1 (TDD)**: RED → GREEN em `mapDatajudRow`/`toIsoTimestamp` (`evidence/red-timestamp-truncation.md`, `evidence/green-timestamp-fix.md`), com a decisão de normalizar por substituição de string em vez de reprocessar via `Date` (`decisions/timestamp-string-normalization.md`).
4. **Fatia 2 (TDD)**: reintrodução verbatim do harness de paridade de mapeamento da PR #1125 (`decisions/reuse-1125-harness.md`), confirmado RED contra o bug original (revertendo a fatia 1 temporariamente) e GREEN com a correção restaurada (`evidence/red-mapping-parity.md`, `evidence/green-mapping-parity.md`).
5. **Validação completa**: vitest 357/357 (+1 sobre a baseline), eslint limpo, typecheck idêntico à baseline (19/0/3), ruff limpo, `pytest -q` limpo à exceção da checagem de completude do próprio relatório em andamento (resolvida por este commit) — ver `checks/full-suite.md`.
6. PR aberta contra `main` com este relatório + o diff — ver `result_summary`/`next_move` no frontmatter.
