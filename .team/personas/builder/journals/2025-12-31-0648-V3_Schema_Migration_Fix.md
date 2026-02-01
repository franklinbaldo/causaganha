---
title: "🏗️ V3 Schema Migration Fix"
date: 2025-12-31
author: "Builder"
emoji: "🏗️"
type: journal
---

## 🏗️ 2025-12-31 - Summary

**Observation:** The initial `TODO.md` was misleading, and the V3 schema migration was incomplete and untested. The CI failures were caused by a combination of a broken migration, missing dependencies, and test environment issues.

**Action:** I followed a strict Test-Driven Development (TDD) process to build a robust and reliable migration:
1.  **🔴 Red:** I created a failing test that exposed the missing migration logic and constraint enforcement.
2.  **🟢 Green:** I implemented a "create-copy-swap" strategy in `src/egregora/database/migrations.py` to safely add `NOT NULL` columns to the `documents` table, backfilling existing rows with default values.
3.  **🔵 Refactor:** I integrated the migration script into the application's startup process in `src/egregora/database/init.py` and fixed E2E test failures by installing missing dependencies and ensuring a placeholder `documents` table exists before the migration runs. I also resolved code coverage issues by running the full E2E suite with the correct `PYTHONPATH`.

**Reflection:** This task highlighted the importance of a robust, version-controlled migration system. The "create-copy-swap" pattern is a reliable way to handle complex schema changes in DuckDB. It also reinforced the need to run all relevant tests, including E2E tests, to catch integration issues that unit tests might miss. For future tasks, I should be more mindful of the project's dependencies and ensure they are all installed before running tests.
