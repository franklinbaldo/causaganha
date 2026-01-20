---
title: "💣 Structured Exceptions for Database Sequences"
date: 2024-07-26
author: "Sapper"
emoji: "💣"
type: journal
---

## 💣 2024-07-26 - Refactoring Database Sequence Error Handling
**Observation:** The `next_sequence_values` method in `src/egregora/database/duckdb_manager.py` was a classic example of an anemic exception. It raised a generic `SequenceError` for multiple, distinct failure modes, including a failure to fetch a value and a failure after a complex connection retry. This forced the caller to parse the error message to understand what went wrong, violating the principle of structured, informative exceptions.

**Action:** I executed a precision TDD-driven refactoring to make these failure modes explicit.
1.  **Established Hierarchy:** I augmented the existing `src/egregora/database/exceptions.py` by defining two new, more specific exceptions: `SequenceFetchError` and `SequenceRetryFailedError`, both inheriting from the base `SequenceError`.
2.  **RED (Tests):** I wrote two new failing tests in `tests/unit/database/test_duckdb_manager.py`. The first test mocked the database cursor to return `None`, asserting that a `SequenceFetchError` was raised. The second test mocked a persistent `duckdb.Error` to ensure a `SequenceRetryFailedError` was raised after the retry logic failed.
3.  **GREEN (Refactor):** I surgically modified the `next_sequence_values` method in `duckdb_manager.py`. I replaced the generic `SequenceError` raises with the new, context-specific `SequenceFetchError` and `SequenceRetryFailedError`, preserving the original exception cause with `from e`.
4.  **VERIFY (Tests):** I ran the test suite and confirmed that my new tests passed and no regressions were introduced.

**Reflection:** This operation successfully replaced a vague, uninformative failure with a clear, structured, and debuggable one. The caller can now programmatically distinguish between a simple fetch failure and a more critical, persistent database error after a retry. This is a significant improvement in the system's robustness. During reconnaissance, I noticed that the `get_table_columns` method in the same `duckdb_manager.py` file swallows `duckdb.Error` and returns an empty set. This is another prime target. A future mission should refactor this to raise a specific `TableInfoError` to make that failure mode explicit instead of returning a potentially misleading empty result.