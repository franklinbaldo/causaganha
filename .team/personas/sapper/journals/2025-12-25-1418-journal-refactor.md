---
title: "💣 Refactored Journaling Exceptions"
date: 2025-12-25
author: "Sapper"
emoji: "💣"
type: journal
---

## 💣 2025-12-25 - Structured Exceptions for Journaling
**Observation:** The `_save_journal_to_file` function in `src/egregora/agents/writer.py` was swallowing specific errors (`TemplateNotFound`, `OSError`) into broad `except` blocks and returning `None`. This violated the "Trigger, Don't Confirm" principle by forcing the caller to handle a nullable return type and hiding the root cause of the failure.

**Action:** I implemented a structured exception hierarchy to make these failure modes explicit.
1.  Created a new `src/egregora/agents/exceptions.py` module.
2.  Defined a base `AgentLogicError` and two specific exceptions: `JournalTemplateError` and `JournalFileSystemError`.
3.  Wrote failing tests to assert that these new exceptions were raised in the appropriate scenarios.
4.  Refactored `_save_journal_to_file` to catch the low-level exceptions and raise the new, context-rich domain exceptions, preserving the original stack trace with `raise ... from e`.
5.  Corrected the function's type hint from `-> str | None` to `-> str`, ensuring type safety.

**Reflection:** This was a clean and successful application of my core philosophy. The resulting code is more robust and easier to debug. A potential next step would be to audit other parts of the `agents` module for similar patterns of error swallowing. The `_execute_writer_with_error_handling` function, for instance, catches a generic `Exception` and wraps it in a `RuntimeError`, which could be a good target for a more specific exception.
