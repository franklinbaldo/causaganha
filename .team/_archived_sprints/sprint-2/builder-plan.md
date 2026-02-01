<<<<<<< HEAD
<<<<<<< HEAD
# Plan: Builder 🏗️ - Sprint 2

**Persona:** Builder 🏗️
**Sprint:** 2
=======
# Plan: Builder - Sprint 2

**Persona:** Builder 🏗️
**Sprint:** 2
**Status:** In Progress
>>>>>>> origin/pr/2860
=======
# Plan: Builder - Sprint 2

**Persona:** Builder (Data Architect)
**Sprint:** 2
>>>>>>> origin/pr/2841
**Created:** 2026-01-26
**Priority:** High

## Objectives
<<<<<<< HEAD
<<<<<<< HEAD

My mission is to provide the data foundation for the new "Context Layer" and ensure the "Batch Era" pipeline remains performant during its refactor.

- [ ] **Implement Git Context Schema:** Design and implement the database schema (`git_commits`, `git_refs`) to support Visionary's "Time Machine" capabilities (RFC 027).
- [ ] **Optimize for Read Performance:** Collaborate with Bolt to identify and implement necessary indexes on the unified `documents` table to eliminate N+1 query bottlenecks.
- [ ] **Support Pipeline Refactor:** Assist Simplifier and Artisan in ensuring their new "ETL" and "Runner" modules interact correctly with the `documents` table, avoiding legacy table usage.
- [ ] **Enforce Strictness:** Ensure all new schemas (Git, Sidecars) launch with comprehensive `CHECK` constraints and Foreign Keys from Day 1.

## Dependencies

- **Visionary:** I need the specific query patterns for the Git Context layer to design the optimal schema (Key-Value vs. Relational).
- **Bolt:** I rely on Bolt's profiling to identify which specific columns need indexing.

## Context

Sprint 2 is "Structure & Polish". While others are refactoring code, I am expanding the data model to include "Time" (Git History). This is a critical enabler for the "Symbiote Shift" in Sprint 3. I am also acting as a guardian to ensure the "Pure" V3 architecture isn't violated during the massive refactors of `write.py` and `runner.py`.

## Expected Deliverables

1.  **New Schemas:** `GIT_COMMITS_SCHEMA` and `GIT_REFS_SCHEMA` in `src/egregora/database/schemas.py`.
2.  **Migration Script:** Migration to create the new Git tables.
3.  **Indexes:** `create_index` calls added to `init.py` for high-traffic columns identified by Bolt.
4.  **Updated Documentation:** `docs/schema-evolution-plan.md` updated with the Git Context layer details.

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Git Cache grows too large | Medium | Medium | Implement specific "Time To Live" (TTL) or "Least Recently Used" (LRU) eviction policies in the schema design (e.g., `last_accessed` column). |
| Refactors bypass `documents` table | Medium | High | I will review Simplifier's and Artisan's PRs to check for legacy table usage. |

## Proposed Collaborations

- **With Visionary:** To finalize the `git_cache` schema.
- **With Bolt:** To review query plans and apply indexes.
- **With Simplifier:** To guide data access patterns in the new ETL module.

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Index overhead on `git_commits` | Low | Medium | I will ensure the index is optimized for the specific access pattern `(path, timestamp DESC)`. |

## Proposed Collaborations
- **With Visionary:** To confirm the exact columns needed for the Git History Resolver.
>>>>>>> origin/pr/2901
=======
| DuckDB Concurrency | Medium | High | Use the centralized `DuckDBStorageManager` for all writes. |
| Schema Evolution Conflicts | Low | Medium | Coordinate with other personas if they are adding new fields; use additive changes only. |

## Proposed Collaborations

- **With Curator:** Discuss if `RunStore` needs to track specific configuration parameters for reproducibility.
- **With Forge:** Ensure the `TaskStore` and `RunStore` APIs are ergonomic for the execution engine.
>>>>>>> origin/pr/2841
