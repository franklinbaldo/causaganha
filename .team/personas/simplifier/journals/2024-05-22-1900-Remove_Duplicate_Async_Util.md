---
title: "📉 Remove Duplicated Async Utility"
date: 2024-05-22
author: "Simplifier"
emoji: "📉"
type: journal
---

## 📉 2024-05-22 - Remove Duplicated `run_async_safely`
**Observation:** The generic utility function `run_async_safely` was defined in two places: `src/egregora/utils/async_utils.py` and `src/egregora/orchestration/pipelines/write.py`. This code duplication increased cognitive load and maintenance overhead.
**Action:** I removed the duplicated function from `write.py` and updated the file to import the canonical version from `async_utils.py`. Before making the change, I created a new test suite for `async_utils.py` to ensure the function's behavior was well-defined and preserved after the refactoring, following a strict TDD approach. This change centralizes the utility and simplifies the codebase.
