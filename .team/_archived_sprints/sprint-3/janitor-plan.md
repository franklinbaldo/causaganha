# Plan: Janitor - Sprint 3

**Persona:** Janitor 🧹
**Sprint:** 3
**Created:** 2026-01-26
**Priority:** Medium

## Objectives
My mission is to perform a "Deep Clean" after the dust settles from the Sprint 2 refactors, and to enforce stricter standards on the new structure.

- [ ] **Post-Refactor Sweep:** Audit the codebase for "refactoring artifacts" (unused imports, commented-out legacy code, temporary shims) left behind by Simplifier and Artisan.
- [ ] **Strict Typing:** Attempt to enable `--strict` mode for `mypy` on the newly refactored `src/egregora/config/` and `src/egregora/orchestration/` modules.
- [ ] **Dependency Audit:** Use `deptry` to verify that the new package structure hasn't introduced unused or transitive dependency violations.
- [ ] **Pre-commit Hardening:** Propose stricter pre-commit hooks (e.g., lower cyclomatic complexity thresholds) now that the code is "simplified".

## Dependencies
- **All Personas:** I need the Sprint 2 refactors to be merged and relatively stable.

## Context
Sprint 3 is "Mobile Polish" and "Discovery" for others, but for me, it is "Consolidation". The code will have changed shape significantly in Sprint 2. My job is to make sure that shape is solid and doesn't have rough edges.

## Expected Deliverables
1.  **Refactor Artifact Removal:** PRs deleting unused code found after the dust settles.
2.  **Strict Mode Config:** `mypy.ini` updates enabling strict mode for core modules.
3.  **Hardened CI:** Updated `.pre-commit-config.yaml`.

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Churn continues into Sprint 3 | Medium | Medium | I will focus on stable modules if the core is still in flux. |
| Strict mode is too painful | Medium | Low | I will apply it incrementally, module by module. |

## Proposed Collaborations
- **With Sentinel:** On stricter security checks in pre-commit.
