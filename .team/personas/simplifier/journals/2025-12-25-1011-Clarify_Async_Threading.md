---
title: "📉 Clarify Async Threading Behavior"
date: 2025-12-25
author: "Simplifier"
emoji: "📉"
type: journal
---

## 📉 2025-12-25 - Clarify `run_async_safely`
**Observation:** The `run_async_safely` function in `src/egregora/utils/async_utils.py` had a misleading docstring. It claimed to use `run_until_complete` when an event loop was already running, but the implementation actually runs the coroutine in a new thread. This discrepancy increases cognitive load for anyone trying to understand the code.

**Action:** I corrected the docstring to accurately describe the threading behavior. This is a pure documentation fix that makes the code easier to understand without changing its logic. I also learned a valuable lesson from a failed first attempt where I tried to change the function's behavior, which was correctly caught in a code review as a violation of my core mission.

**Reflection:** This was a good reminder that simplification isn't just about code; it's also about clarity. Misleading documentation is a form of complexity. In the future, I will be more vigilant about checking that comments and docstrings align with the code's actual implementation. The `utils` directory still has many functions, and I should review them for similar documentation discrepancies.
