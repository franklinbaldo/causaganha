# Plan: Essentialist 💎 - Sprint 3

**Persona:** Essentialist 💎
**Sprint:** 3
**Created:** 2026-01-26
**Priority:** Medium

## Objectives
Sprint 3 is the "Symbiote Shift" (Context Layer). My goal is to ensure this new layer is implemented with radical simplicity, and to finally remove legacy artifacts.

- [ ] **Legacy Cleanup:** Remove the deprecated `att_file` logic and `media` table references from `src/egregora/ops/media.py` and other files. (Delete over Deprecate).
- [ ] **Audit Context Layer:** Review the Visionary's "Code Reference Detector" implementation. Ensure it uses standard tools (Git CLI/Libs) and simple caching (Filesystem/DuckDB), avoiding new infrastructure dependencies.
- [ ] **Enforce "One Good Path":** Ensure the new "Structured Sidecar" doesn't create two ways to do the same thing. If it replaces an old method, the old method must be deleted immediately.

## Dependencies
- **Visionary:** Their work on the Context Layer is the primary subject of my audit.
- **Simplifier:** I expect the `write.py` refactor to be complete, providing a clean base for the cleanup.

## Context
Sprint 3 introduces new capabilities (Git awareness). This is the most dangerous time for complexity growth. We must be ruthless about removing old ways of working (Legacy Media) as we introduce new ones.

## Expected Deliverables
1.  **Deleted Code:** PR removing `att_file` and legacy `media` table logic.
2.  **Architecture Review:** Review of the Context Layer implementation.

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Legacy code remains "just in case" | High | Medium | I will aggressively verify usage and delete unused code. |
| Context Layer becomes over-engineered | Medium | High | I will advocate for "YAGNI" (You Ain't Gonna Need It) on features like complex caching layers. |
