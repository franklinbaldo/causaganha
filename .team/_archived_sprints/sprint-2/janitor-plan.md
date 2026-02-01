# Plan: Janitor - Sprint 2

**Persona:** Janitor 🧹
**Sprint:** 2
**Created:** 2026-01-26
**Priority:** Medium

## Objectives
My mission is to maintain code hygiene alongside the major structural refactors, focusing on Type Safety and Modernization in areas *not* currently under heavy surgery.

- [ ] **Type Safety Campaign:** Tackle the high volume of `mypy` errors in `src/egregora/agents/enricher.py` and `src/egregora/utils/` (excluding `rate_limit.py` if Artisan touches it). Goal: Fix >50 type errors.
- [ ] **Modernization Sweep:** Apply `ruff` modernization rules (SIM, UP) to `src/egregora/data_primitives/` and `src/egregora/transformations/` to improve readability.
- [ ] **Test Stabilization:** Monitor the test suite for flakiness introduced by the new refactors and apply "Strategy D" (Loop Testing) where needed.
- [ ] **Journal Review:** Consolidate learnings from the "Batch Era" cleanup to inform the "Real Time" era patterns.

## Dependencies
- **Artisan & Simplifier:** I must avoid `src/egregora/orchestration/runner.py`, `src/egregora/orchestration/pipelines/write.py`, and `src/egregora/config/` to prevent merge conflicts.
- **Refactor:** I will coordinate to ensure we don't both target the same "dead code".

## Context
Sprint 2 is a "surgery" sprint. While the surgeons (Simplifier, Artisan) are operating on the heart (Runner, Pipeline), I will be cleaning the instruments and keeping the peripheral areas (Enrichers, Utils) sterile.

## Expected Deliverables
1.  **Cleaner Enricher:** Significant reduction in `mypy` errors in the enrichment module.
2.  **Modernized Primitives:** `data_primitives` module updated to modern Python syntax.
3.  **Stable CI:** Fixes for any flaky tests that emerge.

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Merge Conflicts with Artisan | Medium | Medium | I will strictly scope my PRs to files *not* in the Artisan plan. |
| Over-polishing | Low | Low | I will time-box my sessions and focus on objective metrics (error counts). |

## Proposed Collaborations
- **With Refactor:** Sync on which modules are "safe" to clean.
Mon Jan 26 06:37:07 UTC 2026

<!-- Trivial update 2 -->
