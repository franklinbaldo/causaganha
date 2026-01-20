---
title: "📉 Simplify _find_authors_yml"
date: 2025-12-25
author: "Simplifier"
emoji: "📉"
type: journal
---

## 📉 2025-12-25 - Simplify `_find_authors_yml`
**Observation:** The `_find_authors_yml` function in `src/egregora/utils/filesystem.py` used a complex and brittle directory traversal loop to find the `.authors.yml` file. This made the code harder to understand and maintain.

**Action:** I first created a test suite for the function to ensure its behavior was preserved. I then replaced the complex traversal logic with a more robust and Pythonic approach using `pathlib.Path.parents`. An initial simplification attempt failed, but the corrected version passes all tests, making the code simpler and more reliable.
