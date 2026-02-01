# Plan: Streamliner - Sprint 2

**Persona:** Streamliner
**Sprint:** 2
**Created on:** 2026-01-07
**Priority:** High

## Goals

Describe the main goals for this sprint:

- [ ] Profile the full `egregora` pipeline to identify new performance bottlenecks.
- [ ] Investigate `src/egregora/transformations/enrichment.py` for potential vectorization opportunities.
- [ ] Optimize any remaining iterative metadata queries in the orchestration layer.

## Dependencies

List work dependencies from other personas:

- **None** currently identified.

## Context

Explain the context and reasoning behind this plan:

During Sprint 1, I successfully optimized the `_window_by_bytes` function, achieving a ~16x speedup. The windowing module is now largely optimized (count, time, and bytes). The next logical step is to move upstream to the enrichment phase or downstream to the formatting phase to find similar inefficiencies.

## Expected Deliverables

1. **Profiling Report:** A document detailing the performance profile of the main pipeline.
2. **Optimization Plan:** An updated `docs/data-processing-optimization.md` with new targets.
3. **Refactored Enrichment:** If inefficiencies are found, initial refactoring of `enrichment.py`.

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| No obvious bottlenecks found | Low | Medium | Focus on micro-optimizations or database configuration (DuckDB tuning). |

## Proposed Collaborations

- **With Bolt:** Coordinate on overall system latency measurements.

## Additional Notes

Focus remains on "Calculate, Don't Iterate".
