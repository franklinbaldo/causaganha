---
type: AgentGoal
id: "2026-09-06-exciting-mccarthy-488tov-goal-export-import-saved-consultations"
run_id: "2026-09-06-exciting-mccarthy-488tov"
goal: "Let a /minhas-consultas user export their saved processes/searches to a local JSON file and re-import it (same or different browser), entirely client-side, without weakening #1232's change-tracking semantics."
rationale: "Issue #1235 (filed by the repo owner, READY para IMPLEMENTAÇÃO) names a concrete, real gap: /minhas-consultas is deliberately local-first (#908) but that makes continuity fragile — clearing site data or switching browsers loses the whole list with no recovery path. This is the freshest, best-specified, unblocked piece of work available this round (no open PR to resume, no external credential/infra blocker), continuing the same file this project has been actively developing today (#908 -> #1133 -> #1232 -> #1235)."
success_signal: "A new pure module (savedConsultationsBackup.ts) round-trips SavedConsultation[] through export/import with a deterministic merge/dedup rule, proven by tests that fail RED before the module exists and pass GREEN after (round-trip into empty storage, merge into non-empty storage, duplicate handling, corrupted/invalid JSON leaves state untouched, unknown schema_version leaves state untouched); SavedConsultations.svelte gains keyboard- and mobile-usable Exportar/Importar actions wired to that module, verified by component tests; the full web suite (npm run lint/typecheck/test) and Python suite (ruff check/format, pytest -q) stay green; okf-parser check stays conformant."
status: "achieved"
---

# Goal da rodada

Implementar exportação/importação local (sem conta, sem rede) das consultas salvas em `/minhas-consultas`, fechando a issue #1235 com TDD: funções puras de round-trip/merge primeiro, depois a UI.
