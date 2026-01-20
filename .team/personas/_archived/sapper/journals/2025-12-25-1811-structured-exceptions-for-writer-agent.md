---
title: "💣 Structured Exceptions for Writer Agent"
date: 2025-12-25
author: "Sapper"
emoji: "💣"
type: journal
---

## 💣 2025-12-25 - Refactoring Writer Agent Error Handling
**Observation:** The `_execute_writer_with_error_handling` function in `src/egregora/agents/writer.py` was a clear violation of the "Trigger, Don't Confirm" principle. It used a broad `except Exception:` block to catch any failure and wrapped it in a generic `RuntimeError`. This forced the caller to handle an anemic exception and obscured the specific failure mode.

**Action:** I executed a surgical refactoring following the TDD process to address this.
1.  **STRUCTURE:** I defined a new, specific exception, `WriterAgentExecutionError`, in `src/egregora/agents/exceptions.py`. This exception is designed to carry context, specifically the `window_label` of the failed operation.
2.  **RED:** I wrote a failing test, `test_execute_writer_raises_specific_error`, which mocked the underlying agent call to raise a generic `ValueError` and asserted that my new `WriterAgentExecutionError` was raised in its place. The test failed as expected, confirming the existing incorrect behavior.
3.  **GREEN:** I refactored the `except` block in `_execute_writer_with_error_handling` to raise the new `WriterAgentExecutionError`, ensuring the original exception was chained using `from exc` to preserve the stack trace.
4.  **REFACTOR:** I ran the tests again, and they all passed, confirming the refactoring was successful.

**Reflection:** This was a textbook TDD refactoring. The resulting code is more robust, as the caller can now specifically catch `WriterAgentExecutionError` and handle that failure case programmatically. The previous implementation with `RuntimeError` was a dead end for any intelligent error handling. The next logical step would be to audit other agents, such as `enricher.py` or `avatar.py`, for similar patterns of generic exception handling or error swallowing. The goal is to systematically replace all anemic exceptions and `None`-for-error patterns with a rich, explicit exception hierarchy.
