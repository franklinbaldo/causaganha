---
title: "💣 Structured Exceptions for Writer Agent"
date: 2025-12-25
author: "Sapper"
emoji: "💣"
type: journal
---

## 💣 2025-12-25 - Structured Exceptions for Writer Agent
**Observation:** The `_execute_writer_with_error_handling` function in `src/egregora/agents/writer.py` was catching a generic `Exception` and wrapping it in a non-specific `RuntimeError`. This violated the "Trigger, Don't Confirm" principle by obscuring the failure's context and forcing broad, less-informed error handling on the caller.

**Action:** I implemented a structured exception to make this failure mode explicit and informative.
1.  Defined a new `WriterAgentExecutionError` in `src/egregora/agents/exceptions.py`, inheriting from the base `AgentLogicError`. This new exception carries the `window_label` to provide critical context about what part of the data processing failed.
2.  Wrote a failing test in `tests/unit/agents/test_writer.py` to assert that a failure in the underlying agent would raise this new, specific exception.
3.  Refactored `_execute_writer_with_error_handling` to catch the generic exception and raise the new `WriterAgentExecutionError`, preserving the original stack trace with `raise ... from e`.
4.  Ran the tests to confirm the fix, successfully turning the test from RED to GREEN.

**Reflection:** This was another successful application of my core philosophy. The code is now more robust, and failures in the writer agent will be easier to trace and debug. The next logical step is to continue auditing the `agents` module for similar error-swallowing patterns. A quick scan suggests other areas might still be using generic exceptions where more specific, structured ones would be beneficial. I will continue to hunt these down.
