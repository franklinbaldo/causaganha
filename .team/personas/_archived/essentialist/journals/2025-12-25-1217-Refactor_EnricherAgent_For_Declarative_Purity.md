---
title: "💎 Refactor EnricherAgent for Declarative Purity"
date: 2025-12-25
author: "Essentialist"
emoji: "💎"
type: journal
---

## 💎 2025-12-25 - Refactor EnricherAgent
**Observation:** The `EnricherAgent` contained imperative logic for checking media enclosures and verbosely reconstructed `Entry` objects. This violated the "Declarative over imperative" and "Data over logic" heuristics.
**Action:** I moved the media-checking logic to a `has_enclosure` property on the `Entry` model itself. I then refactored the agent to use this property and to use `model_copy` for declarative updates. The entire process was guided by strict TDD.
**Reflection:** The `Entry` and `Document` types are central to the system. Enhancing these core data models with well-tested properties is a high-leverage way to simplify the agents and other components that consume them. Future work should continue to look for opportunities to move business logic from imperative code in agents into declarative properties or methods on the core data types. The existing test failures in unrelated modules should be addressed to improve the overall health of the codebase.
