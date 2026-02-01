---
title: "💣 Structured Exceptions for Profile Management"
date: 2024-07-26
author: "Sapper"
emoji: "💣"
type: journal
---

## 💣 2024-07-26 - Summary

**Observation:** The `src/egregora/knowledge/profiles.py` module was a prime target for refactoring. It heavily relied on "Look Before You Leap" (LBYL) logic, with numerous functions returning `None` to signal failure states. This practice forced callers to perform constant defensive checks and obscured the root causes of errors.

**Action:** I executed a precise, test-driven refactoring of the module's exception handling.
1.  **Established Exception Hierarchy:** Created `src/egregora/knowledge/exceptions.py` with a `ProfileError` base and specific exceptions: `ProfileNotFoundError`, `ProfileParsingError`, and `InvalidAliasError`.
2.  **Enforced EAFP:**
    - Modified `_find_profile_path` and `read_profile` to raise `ProfileNotFoundError`.
    - Modified `_get_uuid_from_profile` to raise `ProfileParsingError`.
    - Modified `_validate_alias` to raise `InvalidAliasError`.
3.  **Refactored Callers:** Updated all functions that used the refactored methods to handle the new exceptions with `try/except` blocks, removing the need for defensive `if` checks.
4.  **TDD Protocol:** For each change, I first wrote a failing test in a new test file (`tests/unit/knowledge/test_profiles.py`), implemented the logic to make it pass, and then verified the result, ensuring the refactoring was safe and correct.

**Reflection:** This mission was a textbook success. The `profiles.py` module is now significantly more robust, and its failure modes are explicit and informative. The EAFP approach has made the code cleaner and easier to reason about. The next logical target would be to investigate the `output_sinks` module, as `grep` revealed it also contains a high density of `return None` statements. A similar surgical refactoring there would likely yield significant improvements in the reliability of the site generation pipeline.
