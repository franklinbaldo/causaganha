---
title: "💣 Structured Config Exceptions"
date: "2023-10-27"
author: "Sapper"
emoji: "💣"
type: journal
---

## 💣 2023-10-27 - Refactoring Config Exception Handling
**Observation:** The configuration loading module (`src/egregora/config/settings.py`) exhibited several anti-patterns. It frequently returned `None` on failure, caught overly broad exceptions, and raised generic `ValueError` exceptions. Most critically, it would swallow `pydantic.ValidationError`, log the error, and then return a default configuration object, completely hiding potentially critical configuration mistakes from the user.

**Action:** I executed a full TDD refactoring of the module's exception handling.
1.  **Established an Exception Hierarchy:** Created a new `src/egregora/config/exceptions.py` file with a clear hierarchy: `ConfigError` as the base, and specific exceptions like `ConfigNotFoundError`, `ConfigValidationError`, `SiteNotFoundError`, `InvalidDateFormatError`, etc.
2.  **Enforced EAFP:** Modified `find_egregora_config` to raise `ConfigNotFoundError` instead of returning `None`.
3.  **Forced Fail-Fast Behavior:** Refactored `load_egregora_config` to catch `pydantic.ValidationError` and re-raise it as a `ConfigValidationError`, ensuring that invalid configurations now halt execution immediately.
4.  **Replaced Generic Exceptions:** Systematically replaced all generic `ValueError` and `TypeError` exceptions with the new, more specific, structured exceptions.
5.  **Wrote Granular Tests:** For each refactoring, I first wrote a failing test to prove the defect, then implemented the change to make the test pass, ensuring the safety and correctness of the new logic.

**Reflection:** This refactoring significantly improves the robustness and debuggability of the application's startup sequence. Configuration errors are now explicit and informative. However, the `create_default_config` function, while now used more predictably, still represents a potential failure point. If the file system is read-only or there are permission issues, the application could still fail in an unstructured way. A future iteration should consider making this file creation process more resilient, perhaps by raising a `DefaultConfigCreationError` if the write operation fails. This would provide a more complete and predictable set of failure modes for the entire configuration lifecycle.
