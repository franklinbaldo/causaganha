---
type: AgentGoal
id: "2026-09-05-exciting-mccarthy-9xpeua-goal-copy-reference-action"
run_id: "2026-09-05-exciting-mccarthy-9xpeua"
goal: "Implement issue #1135: a 'Copiar referência' action on /processo that produces a short, stable, plain-text reference (source, record identification, public origin URL or preserved artifact, freshness when available, CausaGanha URL as secondary context) for the dossier as a whole and for individual JURIS/STJ documents that carry a public origin URL — without inventing fields the dataset does not provide."
rationale: "CLAUDE.md and the OKF knowledge reading both show the last two rounds spent entirely on the AgentRun loop's own infrastructure; the most recent round's next_move explicitly calls for turning back to the product backlog. #1135 is the best-fit next slice: it is READY, self-contained to the web frontend, has no external side effects (no IA credentials, no live workflow runs), and its own acceptance criteria already demand deterministic tests for the reference text format — a natural TDD RED->GREEN slice."
success_signal: "A pure function (buildProcessoReferenceText / buildDocumentoReferenceText) produces the documented reference text deterministically for the dossier header and for a JURIS/STJ document row, with unit tests proving: no placeholder is emitted for a missing date/hash, the CausaGanha URL stays distinguishable from the preserved-origin URL, and the action is wired into ProcessoLookup.svelte only where provenance (an origin URL) actually exists. `npx vitest run` is green on the new and existing processo test files, and a PR is opened against main."
status: "achieved"
---

# Goal: ação "Copiar referência" no dossiê /processo (issue #1135)

Fecha o primeiro slice de #1135: referência textual verificável, reutilizável em petições/notas técnicas, sem inventar proveniência ausente.
