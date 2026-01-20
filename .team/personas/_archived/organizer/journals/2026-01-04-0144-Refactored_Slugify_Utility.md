---
title: "🗂️ Refactored Slugify Utility to Text Module"
date: 2026-01-04
author: "Organizer"
emoji: "🗂️"
type: journal
---

## 🗂️ 2026-01-04 - Summary

**Observation:** The `slugify` function, a generic text utility, was located in `src/egregora/utils/paths.py`. This was a misnomer, as its function is text manipulation, not path calculation, violating the Single Responsibility Principle at the module level.

**Action:**
- Moved the `slugify` function and its related constants to a new, more appropriately named module at `src/egregora/utils/text.py`.
- Updated all consumer imports across the V2 and V3 codebases to point to the new location.
- Renamed the corresponding test file from `test_paths.py` to `test_text.py` and moved it to `tests/unit/utils/`.
- Deleted the now-empty `src/egregora/utils/paths.py` file.

**Reflection:** This was a successful, low-risk refactoring that improves the codebase's logical structure. The `utils` directory often becomes a dumping ground for unrelated functions; this move helps clarify the purpose of each module. The next logical step would be to investigate `src/egregora/utils/datetime_utils.py` to see if its contents are also misplaced and could be moved to a more domain-specific location.