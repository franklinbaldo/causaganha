---
title: "🗂️ Refactored UsageTracker to LLM Module"
date: 2026-01-01
author: "Organizer"
emoji: "🗂️"
type: journal
---

## 🗂️ 2026-01-01 - Summary

**Observation:** The `UsageTracker` class, responsible for tracking LLM token usage, was located in a generic utility module (`src/egregora/utils/metrics.py`). This did not accurately reflect its domain-specific purpose and made the codebase harder to navigate.

**Action:**
1. Created a comprehensive test suite for `UsageTracker` to ensure its behavior was captured before refactoring.
2. Moved the `UsageTracker` class to a new, more appropriate module at `src/egregora/llm/usage.py`.
3. Updated all consumer imports across the application to point to the new location.
4. Relocated the test suite to `tests/unit/llm/test_usage.py` to mirror the new source structure.
5. Deleted the old, now-empty `src/egregora/utils/metrics.py` file and its corresponding test file directory.
6. Ran pre-commit hooks and staged the automated fixes to resolve CI failures.

**Reflection:** This refactoring successfully co-located the LLM usage tracking logic with other LLM-related code, improving modularity and adhering to the Single Responsibility Principle. The initial submission failed CI due to pre-commit hook issues, reinforcing the critical importance of running these checks locally before every submission. Future refactoring work should continue to identify and relocate misplaced utilities to their correct domain-specific modules.
