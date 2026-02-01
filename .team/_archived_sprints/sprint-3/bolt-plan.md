# Plan: Bolt - Sprint 3

**Persona:** Bolt ⚡
**Sprint:** 3
**Created on:** 2026-01-22
**Priority:** Medium

## Objectives
My mission is to enable the "Real-Time Adapter Framework" (Visionary's Moonshot) by optimizing for latency and concurrency, and to finalize the performance hardening of the Context Layer.

- [ ] **Async Core:** Refactor critical blocking I/O paths in the ingestion layer to be fully asynchronous (preparing for real-time streams).
- [ ] **Latency Budget:** Establish and enforce a "Latency Budget" for message processing (e.g., <50ms per message from ingestion to DB).
- [ ] **Stream Processing:** Prototype a stream-based processing model (using `async generators` or `trio`) to replace the batch-windowing logic for the real-time adapter.
- [ ] **Git History Optimization (Finalize):** Ensure the Git history resolution scale linearly with repo size, possibly implementing an incremental updater.
- [ ] **Load Testing:** Conduct load testing on the new architecture to identify breaking points.

## Dependencies

- **Streamliner:** Data pipeline structure

## Context

As the dataset grows, serial processing becomes a bottleneck. Sprint 3 focuses on parallelism and algorithm efficiency.

## Expected Deliverables

1. Parallel media downloader/enricher.
2. Optimized ELO calculation query (DuckDB).
3. Memory profile report for main agents.

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Python GIL limitations | Medium | High | Use multi-processing for CPU-bound tasks (if any), keep the main loop I/O bound. |
| DB Write Locking | Medium | High | Optimizing DuckDB write patterns or moving to a wal-enabled mode if not already. |
