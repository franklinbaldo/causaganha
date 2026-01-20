---
title: "💣 Structured Exceptions for Writer Agent"
date: 2024-07-25
author: "Sapper"
emoji: "💣"
type: journal
---

## 💣 2024-07-25 - Refactoring `egregora.agents.writer`
**Observation:** The `egregora.agents.writer` module exhibited several anti-patterns in its exception handling. It used broad `except Exception` blocks, raised generic `RuntimeError` exceptions that hid the original failure context, and swallowed `KeyError`s by returning empty strings, violating the "Trigger, Don't Confirm" principle.

**Action:** I performed a surgical refactoring guided by Test-Driven Development.
1.  **Established Hierarchy:** I created a new set of specific exceptions in `src/egregora/agents/exceptions.py`: `AgentExecutionError`, `JournalDataError`, and `FormatInstructionError`, all inheriting from the base `AgentLogicError`.
2.  **RED (Tests):** For each refactoring target, I wrote a failing test in `tests/unit/agents/test_writer_logic.py` that asserted the new, specific exception was raised under the correct failure conditions.
3.  **GREEN (Refactor):** I refactored the following functions:
    *   `_save_journal_to_file`: Replaced an incorrect `JournalFileSystemError` with the more accurate `JournalDataError` for data validation failures.
    *   `_execute_writer_with_error_handling`: Replaced a generic `RuntimeError` with `AgentExecutionError`, ensuring the `window_label` and original cause were preserved.
    *   `write_posts_with_pydantic_agent`: Replaced a `RuntimeError` with `AgentExecutionError`.
    *   `load_format_instructions`: Removed the error-swallowing `try/except KeyError` and replaced it with a `try/except` that raises a descriptive `FormatInstructionError`.
4.  **VERIFY (Tests):** I ran the relevant unit tests (`test_writer_logic.py`) to confirm all new tests passed and no regressions were introduced.

**Reflection:** This was a successful mission that significantly improved the robustness of the writer agent. The failures are now explicit and carry critical context, which will make debugging much easier. The `writer.py` module is large and still contains complex logic. A future iteration could investigate the `_prepare_deps` function, which raises a generic `ValueError`. This could be a good candidate for a more specific `AgentDependencyError` to better pinpoint setup failures. The overall principle of replacing defensive checks and generic exceptions with specific, structured ones has proven effective.
