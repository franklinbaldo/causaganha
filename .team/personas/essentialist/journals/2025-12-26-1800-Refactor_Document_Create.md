---
title: "💎 Refactor Document.create to Declarative Validator"
date: 2025-12-26
author: "Essentialist"
emoji: "💎"
type: journal
---

## 💎 2025-12-26 - Refactor Document.create to Declarative Validator

**Observation:** The `Document.create` factory method and its subclass override `WikiPage.create_concept` were imperative workarounds that violated the "Declarative over imperative" and "Composition over inheritance" heuristics. This complex, multi-step instantiation logic forced consumers to use special factories instead of the standard Pydantic constructor, making the core data models difficult to extend and test.

**Action:** I refactored the `Document` class to use a Pydantic `model_validator` for declarative identity generation. This involved moving the slug and ID generation logic from the `create` factory directly into the model's validation lifecycle. Subsequently, I deleted the redundant `create` methods from both `Document` and `WikiPage`. The entire process was guided by strict Test-Driven Development, which began with writing failing tests for the desired constructor behavior and then methodically fixing a cascade of broken tests across the entire application to align them with the new, simpler API.

**Reflection:** This refactoring is a strong example of the "Data over logic" heuristic. By embedding the identity generation logic declaratively within the `Document` model itself, we simplify all consuming code. The constructor is now the single, reliable path for instantiation, eliminating the cognitive overhead of special factory methods. The widespread test failures demonstrated how a single heuristic violation in a core component can ripple complexity throughout the system. Fixing them has not only corrected the immediate issue but also made the entire test suite more robust. Future work should investigate other core data models, such as the `Feed` object, for similar opportunities to replace imperative logic with declarative validation.