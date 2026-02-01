<<<<<<< HEAD
<<<<<<< HEAD
# Plan: Builder 🏗️ - Sprint 3
=======
# Plan: Builder - Sprint 3
>>>>>>> origin/pr/2860

**Persona:** Builder 🏗️
**Sprint:** 3
**Created:** 2026-01-26
<<<<<<< HEAD
**Priority:** Medium

## Objectives

My mission is to support the "Symbiote Shift" by enabling the storage of deep context and self-reflection data.

- [ ] **"Structured Sidecar" Schema:** Formalize the data model for "Structured Sidecars" (metadata accompanying source files) as defined by the Visionary.
- [ ] **Autopoiesis Data Support:** Create schemas to store agent "Self-Correction" logs (Critique -> Action -> Outcome) to enable the feedback loop.
- [ ] **Advanced Git Context:** Expand the Git schema to support finer-grained code references (potentially AST-level symbols) if required.

## Dependencies

- **Visionary:** Requirements for the "Structured Sidecar" and "Autopoiesis" loops.
- **Meta:** Requirements for storing system introspection data.

## Context

Sprint 3 is about the agent becoming a "Symbiote" that lives alongside the code. The database must evolve from a passive store of documents to an active memory of the codebase's history and the agent's own thought processes.

## Expected Deliverables

1.  **Sidecar Schema:** Definitions for storing/indexing sidecar data.
2.  **Feedback Loop Tables:** Schema for storing `agent_critiques` and `agent_actions`.
3.  **Expanded Git Schema:** If needed, tables for `code_symbols` linked to Git refs.

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Schema complexity explosion | Medium | High | Maintain the "Structure Before Scale" philosophy. Only add tables that are strictly necessary and enforce them with constraints. |

## Proposed Collaborations

- **With Visionary:** Deep collaboration on the Symbiote data model.
- **With Meta:** On storing introspection data.

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| DuckDB VSS performance is poor | Medium | High | Benchmark early. If poor, we stick with LanceDB but document it as an explicit "Sidecar". |
| Real-Time writes lock the DB | High | High | Investigate `IMMEDIATE` vs `DEFERRED` transaction modes and potential use of an ingestion buffer (which we already have in `messages` table). |
>>>>>>> origin/pr/2901
=======
| Index Build Time | Medium | Medium | Run index creation in background or during maintenance windows. |
| Data Loss during Archival | Low | High | Implement "Copy-Verify-Delete" protocol for archival. |

## Proposed Collaborations

- **With Curator:** Define the specific query patterns needed for semantic search (e.g., k-NN vs. range search).
>>>>>>> origin/pr/2841
