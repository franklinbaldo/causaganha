# Plan: Sapper - Sprint 2

**Persona:** Sapper 💣
**Sprint:** 2
**Created:** 2026-01-26
**Priority:** High

## Objectives
My mission is to ensure the new "Structure" components (Config, ETL) adhere to the "Trigger, Don't Confirm" philosophy.

- [ ] **Refactor Input Adapter Registry:** Replace generic `KeyError` and `ValueError` with `UnknownAdapterError` in `registry.py` and `ADAPTER_REGISTRY` access.
- [ ] **Audit New ETL Exceptions:** Collaborate with Simplifier to ensure the new `src/egregora/orchestration/pipelines/etl/` package has a proper exception hierarchy (`EtlError`).
- [ ] **Audit Config Exceptions:** Collaborate with Artisan to ensure `ConfigurationError` wraps Pydantic's `ValidationError`.
- [ ] **Eliminate LBYL in Utils:** Identify and refactor at least one utility module (e.g., `utils/io.py` or similar) to remove "Look Before You Leap" patterns.

## Dependencies
- **Simplifier:** I need visibility into the ETL extraction PRs.
- **Artisan:** I need visibility into the Config refactor PRs.

## Context
Sprint 2 is about solidifying the structure. If we build this structure on top of generic `Exception` or defensive `return None` checks, we will pay for it forever. I must intervene early in the refactoring process.

## Expected Deliverables
1.  **New Module:** `src/egregora/input_adapters/exceptions.py`.
2.  **Refactored Registry:** `src/egregora/input_adapters/registry.py` using specific exceptions.
3.  **Exception Hierarchies:** Defined exceptions for ETL and Config (in collaboration).

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Refactors Merge Generic Exceptions | High | High | I will aggressively review PRs from Simplifier and Artisan. |
