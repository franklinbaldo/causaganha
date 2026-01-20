---
title: "🎭 Make `egregora demo` resilient to API errors"
date: 2024-01-16
author: "Curator"
emoji: "🎭"
type: task
---

## 🎭 Make `egregora demo` resilient to API errors

**Observation:**
The `egregora demo` command currently fails and exits prematurely when it encounters an API error (e.g., rate limiting from the Google Gemini API). This leaves the `demo` directory in an incomplete state, often missing the crucial `.egregora/mkdocs.yml` file, which blocks any further UX evaluation.

**Action:**
Modify the `egregora demo` command to handle API errors gracefully. The command should:
1.  Catch API errors during the content generation phase.
2.  Log the error to the console for the user to see.
3.  Continue with the site scaffolding process, even if content generation fails.
4.  Ensure that a complete "empty state" of the demo site is always generated, including the `.egregora/mkdocs.yml` file.

**Reflection:**
A resilient demo command is essential for an efficient Curation Cycle. By ensuring that a complete, buildable "empty state" is always generated, we can unblock UX evaluation and development, even when external services are unavailable. This aligns with the UX principle of "Graceful Degradation."
