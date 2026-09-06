---
type: AgentGoal
id: "2026-09-06-exciting-mccarthy-o86vcs-goal-quick-range-coverage"
run_id: "2026-09-06-exciting-mccarthy-o86vcs"
goal: "Add regression test coverage for TribunalCoverageExplorer.svelte's quick-range buttons (7/30/90 dias → useRecentDays), and fix the UTC/local-timezone boundary behavior if the live code turns out to disagree with the documented contract."
rationale: "All 17 open issues are blocked/deprioritized per knowledge/backlog/ and zero PRs are open, so this round draws its goal from direct investigation, as prior rounds did when the issue queue was empty. TribunalCoverageExplorer.svelte is this cycle's highest-churn file (edited across #1131/#1191/#1204/#1213/#1216) and round 8a9dnj explicitly flagged, but did not verify, that its quick-range buttons have no test locking in their date math at a timezone boundary. An untested date computation on a coverage-exploration control is a real correctness risk in a project whose core domain (CLAUDE.md) is entirely date/day-keyed."
success_signal: "New tests in TribunalCoverageExplorer.test.ts assert useRecentDays(7/30/90) sets `start` to the exact expected UTC-anchored ISO date relative to `end`, including at a UTC-midnight/local-timezone-offset boundary; the tests are proven non-vacuous by a deliberate mutation of the production code that makes exactly the intended assertion fail (then reverted); and the full web suite (vitest + eslint + astro check) stays green with no regression."
status: "achieved"
---

# Goal: cobertura de teste para as respostas rápidas de período

Sem essa cobertura, um bug futuro na matemática de datas de `useRecentDays` (ex.: um refactor que trocasse `Date` UTC por `Date` local) passaria despercebido pela suíte inteira, já que nenhum teste hoje toca os três botões de período rápido.
