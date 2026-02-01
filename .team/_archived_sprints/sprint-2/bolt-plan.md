# Plan: Bolt - Sprint 2

**Persona:** Bolt ⚡
**Sprint:** 2
**Created on:** 2026-01-22
**Priority:** High

## Objectives
My mission is to ensure the major refactors (Runner/Write pipeline) do not degrade performance, and to assist in high-performance implementations of new features (Git History, Social Cards).

- [ ] **Baseline Profiling:** Create a comprehensive benchmark suite for the current `write` pipeline (before Simplifier/Artisan refactors land) to detect regressions.
- [ ] **Efficient Git History Loading:** Prototype a fast, bulk-loading mechanism for Git history (using `git log` + DuckDB/Pandas) to support Visionary's `GitHistoryResolver`, avoiding the N+1 subprocess call trap.
- [ ] **Social Card Caching:** Review and assist Forge in implementing hash-based caching for social card generation to prevent build slowdowns.
- [ ] **Ibis/DuckDB Optimization:** Audit `src/egregora/transformations/` for N+1 query patterns and optimize them using vectorized operations.
- [ ] **Review Refactors:** Actively review PRs from Simplifier and Artisan with a focus on import overhead and initialization latency.

## Dependencies
- **Simplifier/Artisan:** I need to coordinate with their refactors to ensure my benchmarks remain valid or are updated.
- **Visionary:** My Git history work supports their RFC 027 implementation.
- **Forge:** My caching advice supports their Social Card feature.

## Context
Sprint 2 is a "Refactor Sprint" for others. For me, it is a "Defense Sprint" (preventing regressions) and an "Enabling Sprint" (providing fast building blocks for new features).

## Expected Deliverables
1.  **Pipeline Benchmark Suite:** A new set of `pytest-benchmark` tests for the full pipeline.
2.  **Git Loader Prototype:** A standalone script or module demonstrating sub-second loading of repository history.
3.  **Optimized Queries:** PRs to fix inefficient Ibis expressions.

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Refactors break benchmarks | High | Medium | I will create modular benchmarks that test components (ETL, Windowing) in isolation, not just the full pipeline. |
| Visionary implements slow Git lookups | High | High | I will provide the optimized "Bulk Load" pattern proactively before they finalize their implementation. |
