---
type: AgentRun
id: "2026-09-06-exciting-mccarthy-b0lycs"
started_at: "2026-09-06T07:24:57Z"
completed_at: "2026-09-06T07:50:00Z"
branch_at_start: "claude/exciting-mccarthy-b0lycs"
commit_at_start: "e2d70be5670d39831d3687d67211791682e9d160"
claude_md_reading_id: "2026-09-06-exciting-mccarthy-b0lycs-reading-claude-md"
issues_reading_id: "2026-09-06-exciting-mccarthy-b0lycs-reading-issues"
prs_reading_id: "2026-09-06-exciting-mccarthy-b0lycs-reading-prs"
okf_reading_id: "2026-09-06-exciting-mccarthy-b0lycs-reading-okf"
goal_ids:
  - "2026-09-06-exciting-mccarthy-b0lycs-goal-fix-stats-payload-regression"
primary_goal_id: "2026-09-06-exciting-mccarthy-b0lycs-goal-fix-stats-payload-regression"
considered_work:
  - "#1132 (explorador: receitas executáveis) — READY para implementação mas sem pressão de continuidade nem regressão; deprioritized in favor of #1191."
  - "#1022/#1011/#985 (TCU/TSE Internet Archive publication) — precisa de sign-off humano para upload credenciado ao vivo; rejeitado, inalterado desde rodadas anteriores."
  - "#950/#951 (MCP remote hosting) — decisão de hospedagem ao vivo; rejeitado, inalterado."
  - "#1047/#1050-1057/#884/#886/#887 (segmenter roadmap) — precisa de anotação real/GPU; rejeitado, inalterado."
  - "#1191 (perf(web): não hidratar /stats com o tribunal_calendar inteiro) — selecionado: regressão de prioridade alta, aberta pelo dono ~20 minutos antes desta rodada, follow-up direto da PR que a rodada anterior mesclou (#1189/#1131), com critérios de aceite explícitos e um padrão saudável já existente no código (/publicacoes/[tribunal]) para seguir."
selected_work: "Fixed issue #1191: /stats' drill-down island (TribunalCoverageExplorer, client:only=\"svelte\") was receiving the entire tribunal_calendar contract (~13.9MB, every tribunal x date in the archive) as a serialized `calendarRows` prop, even though the UI only ever renders one tribunal's days at a time — client:only still serializes its props into the page for hydration. Replaced this with build-time per-tribunal partitioning: scripts/render_queries.py now splits the rendered tribunal_calendar.json into web/public/data/tribunal_calendar_by_tribunal/<tribunal>.json right after rendering the canonical contract (same source of truth, no second copy), and TribunalCoverageExplorer.svelte fetches only the selected tribunal's partition client-side (web/src/lib/tribunalCalendarPartition.ts), refetching on tribunal change with a request-sequence guard against races, and showing a loading/error state. Followed TDD throughout: wrote failing tests for the new TS partition module, the rewritten Svelte component (fetch-based, mocking global.fetch), the Python partitioning function, and a grep-based regression gate (TribunalCoverageExplorer.payloadBudget.test.ts) before implementing each. Also caught and fixed a real second-order regression this change would otherwise have introduced in an existing integration test (renderedContracts.integration.test.ts, which recursively validates every file under rendered public/data/ against a registered frontend contract) by excluding the new partition directory from 1:1 contract matching and adding a dedicated parity assertion instead. First attempt at the fix (writing partitions from stats.astro's own frontmatter via node:fs, mirroring the existing OG-SVG-generation pattern) was implemented, tested end-to-end with a local `npm run build`, found not to reach dist/ (Astro copies public/ before running page frontmatter), and replaced with the Python-side approach — recorded as this round's AgentDecision."
expected_behavior: "TribunalCoverageExplorer.svelte no longer declares a bulk calendarRows prop and only ever fetches the currently selected tribunal's partition (verified: a component test asserts every fetch call matches a per-tribunal URL, never the global tribunal_calendar.json). stats.astro stops touching node:fs entirely; scripts/render_queries.py writes the partitions before `npm run build` runs, so Astro's public/ copy step picks them up (verified end-to-end: dist/data/tribunal_calendar_by_tribunal/<tribunal>.json exists after build, dist/stats.html contains zero occurrences of the removed calendarRows prop). #1131's existing behavior (uploaded/absent/sem_evidencia, coveragePct=null when unobserved, shareable tribunal/start/end URL, parity with the canonical contract) is unchanged, covered by the same (adapted) test suite plus the pre-existing tribunalCoverageDrilldown.test.ts (untouched). npm test (418/418), npm run lint (0 errors), npm run build all pass; npm run typecheck's 19 errors are pre-existing and unrelated (diffed against baseline). uv run ruff check / ruff format --check / pytest -q all pass except the expected mid-round AgentRun-completeness test. A regression gate test (TribunalCoverageExplorer.payloadBudget.test.ts) fails if the bulk prop or its wiring reappears."
entry_state: "new"
target_state: "merged"
decision_ids:
  - "2026-09-06-exciting-mccarthy-b0lycs-decision-partition-in-python-not-astro-fs-write"
evidence_ids:
  - "2026-09-06-exciting-mccarthy-b0lycs-evidence-red-green-partition-module"
  - "2026-09-06-exciting-mccarthy-b0lycs-evidence-red-green-component-and-python-partition"
  - "2026-09-06-exciting-mccarthy-b0lycs-evidence-build-payload-before-after"
  - "2026-09-06-exciting-mccarthy-b0lycs-evidence-pr-1192-merged"
check_ids:
  - "2026-09-06-exciting-mccarthy-b0lycs-check-web-suite"
  - "2026-09-06-exciting-mccarthy-b0lycs-check-python-gates"
result_state: "merged"
result_summary: "Implemented and verified end-to-end (component tests, Python tests, a regression gate, and a real npm run build with before/after byte-level inspection of dist/) the fix for issue #1191: /stats no longer ships the entire ~13.9MB tribunal_calendar contract as a client:only island prop. Partitioning moved to scripts/render_queries.py (after a first attempt in stats.astro's own frontmatter was tried, verified not to reach dist/, and replaced — see AgentDecision). All local gates green except the expected mid-round completeness check. PR #1192 (https://github.com/franklinbaldo/causaganha/pull/1192) opened closing #1191, all CI checks passed, and it was merged into main as commit 35ea8f0 within minutes of opening — no review comments, no CI failures, no merge conflict to handle. This follow-up commit records that outcome on a branch restarted from the new main, per this project's established pattern (prior rounds' PRs #1181/#1184/#1186/#1188/#1190 did the same)."
next_move: "#1191 is closed. The next most-recently-updated actionable issue with no owner narrowing comment yet and no continuity pressure from a just-merged PR is #1132 (explorador: receitas executáveis) — READY para implementação per the owner. Also worth a fresh look: whether #1131's drill-down (now payload-fixed) surfaces any other adversarial-review follow-up the way #1189 did, before starting new work. The deferred backlog (#1133 already shipped, #1093 explicitly not urgent) and the non-web candidates (segmenter #1047 roadmap, TCU/TSE IA publication #1022/#1011/#985, MCP remote hosting #950/#951) remain gated exactly as this and prior rounds assessed."
---

# Agent run — 2026-09-06-exciting-mccarthy-b0lycs

Rodada do loop horário do CausaGanha, orientada pelo scaffold `.claude/agent-run-scaffold.md`.

## O que aconteceu

1. **Leituras** (`readings/`): `CLAUDE.md` (fronteira CSS ainda correta, sem deriva), issues abertas (19 — `#1191` no topo, regressão de prioridade alta aberta ~20 min antes da rodada), PRs abertas (0) e conhecimento OKF (bundle conformante, 341 conceitos no início).
2. **Objetivo**: corrigir a regressão de payload de `/stats` (#1191) — o contrato `tribunal_calendar` inteiro (~13,9MB) estava sendo serializado como prop da ilha `client:only` `TribunalCoverageExplorer`.
3. **TDD**: testes vermelhos escritos primeiro para o módulo TS de particionamento, o componente Svelte reescrito (fetch por tribunal), a função Python de particionamento e um gate de regressão — cada um implementado até ficar verde.
4. **Decisão**: a primeira tentativa (escrever partições de dentro do `stats.astro` via `node:fs`, no padrão do SVG de OG) não chegava ao `dist/` — o Astro copia `public/` antes do frontmatter das páginas rodar. Movido para `scripts/render_queries.py`, que já roda antes do `npm run build`.
5. **Evidência**: build real antes/depois mostrando `calendarRows` presente uma vez no HTML antigo e ausente no novo; partição confirmada presente no `dist/` final.
6. Ver `goals/`, `decisions/`, `evidence/` e `checks/` para o detalhe tipado de cada etapa.
