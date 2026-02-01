# Plan: Absolutist - Sprint 2

**Persona:** Absolutist 💯
**Sprint:** 2
**Created:** 2026-01-26
**Priority:** High

## Objectives
My mission is to enforce the "One Way" principle during the massive structural refactoring of this sprint. I will ensure that old patterns are removed, not just deprecated.

<<<<<<< HEAD
- [ ] **Remove `DuckDBStorageManager` Compatibility Shim:** The `src/egregora/database/duckdb_manager.py` file contains a backward compatibility layer for callers expecting a direct connection. I will investigate usage and remove this if confirmed obsolete.
- [ ] **Audit `prompts.py` Compatibility:** Investigate `src/egregora/resources/prompts.py` for "API compatibility with the old prompt_templates.py" and remove if unused.
- [ ] **Post-Migration Cleanup (Config):** Coordinate with **Artisan** to remove legacy dictionary-based configuration loading logic after their Pydantic migration is complete.
- [ ] **Identify New Targets:** Continue scanning the codebase for `legacy`, `deprecated`, and `compat` markers.

## Dependencies
- None specific, but I must coordinate with **Refactor** and **Simplifier** to ensure I don't delete code they are actively modifying.
=======
- **Artisan:** I will wait for their Pydantic migration before touching `config.py` cleanup.
- **Refactor:** Coordinate to ensure I don't delete code they are actively modifying.
>>>>>>> origin/pr/2837

## Context
Sprint 2 is a "Structure" sprint. This is the prime opportunity to reduce technical debt. If we refactor without removing the old code, we double the complexity. I am the garbage collector for this sprint.

## Expected Deliverables
<<<<<<< HEAD
1.  Removal of `DuckDBStorageManager` legacy accessors.
2.  Cleaned up `prompts.py` if safe.
<<<<<<< HEAD
3.  Updated `absolutist-plan.md` for Sprint 3.
=======
The removal of `DuckDBStorageManager.execute` (completed in Sprint 1) was a good start. Now I focus on the prompt system and ensuring the visual identity transition (CSS) is clean.

## Expected Deliverables
1.  Report on `prompts.py` usage and potential for removal.
2.  Clean bill of health for CSS assets.
3.  List of media markers targeted for Sprint 3 removal.
>>>>>>> origin/pr/2890
=======
3.  Removal of legacy configuration loading (if Artisan completes their task).
4.  Updated `absolutist-plan.md` for Sprint 3.
>>>>>>> origin/pr/2837

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Refactors keep compatibility layers "just in case" | High | Medium | I will rigorously comment on PRs requesting removal of shims unless a specific migration plan exists. |
| Deleting code breaks obscure tests | Medium | High | I will run the full test suite (`uv run pytest`) before any removal. |

## Proposed Collaborations
- **With Simplifier:** Verify removal of `write.py` legacy logic.
- **With Artisan:** Verify removal of `config.py` dict logic.
