---
title: "🔨 Refactor Filesystem Authors"
date: 2025-12-25
author: "Artisan"
emoji: "🔨"
type: journal
---

## 🔨 2025-12-25 - Extracted Author Logic from Filesystem
**Observation:** The `src/egregora/utils/filesystem.py` module contained a mix of general file I/O utilities and specific logic for managing `.authors.yml` files. This violated the Single Responsibility Principle, making the code harder to understand, test, and maintain.

**Action:** I refactored the codebase by extracting all author-related functions into a new, dedicated module: `src/egregora/utils/authors.py`. This included moving the functions, updating their visibility (from private to public), and creating a new test file to validate the behavior of the new module. The original `filesystem.py` now imports from the `authors.py` module, cleanly separating the concerns.

**Reflection:** This was a straightforward and high-impact refactoring. A good next step would be to examine other "utility" modules (`datetime_utils.py`, `paths.py`, etc.) for similar opportunities. Often, utility modules become a dumping ground for unrelated functions. By continuing to apply the Single Responsibility Principle, we can create a more modular and maintainable codebase.
