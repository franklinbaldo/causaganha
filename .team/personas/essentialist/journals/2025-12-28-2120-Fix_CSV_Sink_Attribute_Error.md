---
title: "💎 Fix CSV Sink AttributeError"
date: 2025-12-28
author: "Essentialist"
emoji: "💎"
type: journal
---

## 💎 2025-12-28 - Summary

**Observation:** The  in  was crashing with an  because it was attempting to call a non-existent method, , on the  object. This violated the "Data over logic" heuristic, as the sink correctly assumed that the  model should be responsible for its own filtering logic.

**Action:** I fixed this bug by implementing the missing  method on the  model in . This change involved a strict Test-Driven Development (TDD) process, where I first created a failing test that reproduced the bug, and then implemented the method to make the test pass.

**Reflection:** This was a textbook example of the "Data over logic" principle. The original error was a strong signal that the  model was incomplete. By adding the filtering logic directly to the  object, the  becomes a simpler, more declarative component that is less likely to break in the future. Future work should continue to look for opportunities to move business logic from infrastructure components into the core data models they operate on.
