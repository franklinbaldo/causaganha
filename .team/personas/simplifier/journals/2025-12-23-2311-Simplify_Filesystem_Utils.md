---
title: "📉 Simplify Filesystem Utils"
date: 2025-12-23
author: "Simplifier"
emoji: "📉"
type: journal
---

## 📉 2025-12-23 - Simplify Filesystem Utils
**Observation:** The `_extract_clean_date` function in `src/egregora/utils/filesystem.py` contained redundant and fragile date validation logic. Additionally, the `write_markdown_post` function used repetitive `if` statements to build the frontmatter dictionary.
**Action:** I refactored `_extract_clean_date` to use a `try...except` block with `date.fromisoformat`, which is cleaner and more robust. I simplified `write_markdown_post` by replacing the repeated `if` checks with a loop over a list of optional keys. These changes reduce cognitive load and improve maintainability without changing behavior.
