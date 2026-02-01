# Plan: Artisan 🔨 - Sprint 2

**Persona:** Artisan 🔨
**Sprint:** 2
**Created:** 2026-01-26
**Priority:** High
**Reviewed:** 2026-01-26

## Objectives
My mission is to elevate the codebase through superior craftsmanship. For Sprint 2, I will focus on improving type safety and decomposing complex code, strictly adhering to the "Structure & Polish" theme.

<<<<<<< HEAD
- [ ] **Migrate to Pydantic Configuration:** Refactor `src/egregora/config/settings.py` (and related files) to use Pydantic models. This will eliminate `dict` usage for configuration, providing type safety, validation (e.g., `DirectoryPath`), and support for `SecretStr` (collaborating with Sentinel).
- [ ] **Decompose `runner.py`:** The `PipelineRunner` class is a monolith. I will extract distinct responsibilities:
    -   Extract `_process_window` logic into a focused helper or class.
    -   Separate "Worker Construction" from "Pipeline Execution".
    -   Ensure the new interface is compatible with Simplifier's new ETL modules.
- [ ] **Documentation Blitz:** Add Google-style docstrings to at least two key `utils` modules (e.g., `src/egregora/utils/filesystem.py`, `src/egregora/utils/datetime_utils.py`) to improve DX.
- [ ] **Eradicate `Any` in Core:** Target `src/egregora/orchestration/context.py` or similar core files to replace `Any` with strict Protocols or Types.

## Dependencies
- **Simplifier:** I must coordinate with Simplifier on the boundary between `write.py` (ETL) and `runner.py` (Orchestration). We need to agree on the data structures passed between them.
- **Sentinel:** I rely on Sentinel's requirements for `SecretStr` and security validation rules for the new Pydantic config models.
- **Refactor:** I will check `Refactor`'s plan to avoid touching the same `utils` files simultaneously.

## Context
The codebase has reached a level of complexity where "dictionaries passing data" is no longer sustainable. We need rigid contracts (Pydantic Models, Protocols). Also, `runner.py` and `write.py` are the two biggest maintenance burdens. Splitting them up is critical for the "Batch Era".

## Expected Deliverables
1.  **`src/egregora/config/settings.py`**: Fully typed Pydantic implementation.
2.  **Refactored `runner.py`**: Reduced cyclomatic complexity and line count.
3.  **Docstrings**: 100% coverage for 2+ utility modules.
4.  **Type Safety**: Reduced usage of `Any` in orchestration layer.
=======
My mission is to elevate code quality, focusing on type safety and documentation during this "Finish and Polish" sprint.

- [ ] **Strict Typing for ETL Pipeline:** As Simplifier extracts logic to `src/egregora/orchestration/pipelines/etl/`, I will ensure all new functions have strict type hints (no `Any`) and pass `mypy --strict`.
- [ ] **Documentation Audit (Rendering):** The `src/egregora/rendering/` package is critical for the "Portal" theme but lacks comprehensive docstrings. I will add Google-style docstrings to all public functions and classes.
- [ ] **Refine `runner.py` Typing:** Continue the effort to remove `Any` types from the core pipeline runner, specifically improving the `PipelineContext` type safety.

## Dependencies
- **Simplifier:** I depend on Simplifier's extraction of the ETL logic to `src/egregora/orchestration/pipelines/etl/`.

## Context
Sprint 2 is about polish. For code, "polish" means clarity (documentation) and robustness (typing). The rendering engine is the heart of the user experience updates (Forge/Curator), so ensuring its code is well-documented is vital for maintainability.

## Expected Deliverables
1.  **Typed ETL Module:** `src/egregora/orchestration/pipelines/etl/` passing strict type checks.
2.  **Documented Rendering Package:** 100% docstring coverage for `src/egregora/rendering/`.
3.  **Refactored `runner.py`:** Improved type definitions for context and state.
>>>>>>> origin/pr/2886

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Config Refactor breaks runtime | High | High | I will write a "Config Snapshot" test before starting to verify the new Pydantic config produces the exact same values as the old dict config. |
| Runner Refactor conflicts with Simplifier | Medium | High | Early agreement on interfaces. I will review Simplifier's PRs and vice-versa. |
| Import Time Regression | Medium | Medium | I will run `python -X importtime` before and after major refactors to ensure no regression. |

## Proposed Collaborations
- **With Simplifier:** Joint design session for the Pipeline Interface.
- **With Sentinel:** Pair programming on `SecretStr` implementation.
- **With Bolt:** Request benchmarks for the new `runner.py`.
