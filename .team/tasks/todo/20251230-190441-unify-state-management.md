---
id: 20251230-190441-unify-state-management
status: todo
title: "Unify State Management in Provider Rotators"
created_at: "2025-12-30T19:04:41Z"
target_module: "src/egregora/llm/providers/model_cycler.py"
assigned_persona: "artisan"
---

## Description

The `GeminiKeyRotator` and `GeminiModelCycler` classes in `src/egregora/llm/providers/model_cycler.py` have different state management strategies.

- `GeminiKeyRotator` maintains its state (`current_idx`) across multiple `call_with_rotation` invocations, ensuring that load is distributed across API keys even on successful calls. It only resets when `reset()` is called explicitly.
- `GeminiModelCycler`, on the other hand, calls `self.reset()` at the beginning of every `call_with_rotation`, meaning it always starts from the first model in the list.

This inconsistency is subtle and can lead to unexpected behavior. The model cycler will always try the same models in the same order, while the key rotator will distribute the load.

## Task

1.  **Analyze:** Determine the desired behavior for both classes. Should they both maintain state across calls, or should they both reset? The stateful approach of `GeminiKeyRotator` seems more robust for load distribution.
2.  **Unify:** Refactor the classes to use a consistent state management strategy.
3.  **Document:** Add clear docstrings to both classes explaining the chosen state management behavior.

## Acceptance Criteria

- The state management strategy is consistent across `GeminiKeyRotator` and `GeminiModelCycler`.
- The behavior is clearly documented in the class docstrings.
- Existing functionality remains intact, and tests are updated if necessary.
