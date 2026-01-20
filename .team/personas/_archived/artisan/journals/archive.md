---
title: "🔨 Historical Archive"
date: 2025-05-15
author: "Artisan"
emoji: "🔨"
type: journal
---

## 2025-05-15 - CLI Error Handling and Navigation Polish
**Friction:** CLI errors were printed using raw `traceback.print_exc()`, which is ugly and hard to read compared to the rest of the Rich-enhanced UI.
**Solution:** Replaced `traceback.print_exc()` with `console.print_exception(show_locals=False)` in `src/egregora/cli/main.py` to use Rich's beautiful traceback formatting.
**Result:** Errors are now syntax-highlighted and consistent with the application's design language.
