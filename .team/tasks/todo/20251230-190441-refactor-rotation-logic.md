---
id: 20251230-190441-refactor-rotation-logic
status: todo
title: "Refactor Duplicated Rotation Logic in Providers"
created_at: "2025-12-30T19:04:41Z"
target_module: "src/egregora/llm/providers/model_cycler.py"
assigned_persona: "refactor"
---

## Description

The `GeminiKeyRotator` and `GeminiModelCycler` classes in `src/egregora/llm/providers/model_cycler.py` contain nearly identical logic for cycling through a list of items (keys or models) and selecting the next available one. This code duplication increases maintenance overhead and violates the DRY (Don't Repeat Yourself) principle.

## Task

Extract the common rotation logic from `GeminiKeyRotator.next_key` and `GeminiModelCycler.next_model` into a generic, reusable utility class or function. This new utility should handle the state management of the current index and the set of exhausted items.

## Acceptance Criteria

- A new generic rotator utility is created.
- `GeminiKeyRotator` and `GeminiModelCycler` are refactored to use the new utility.
- Existing functionality and tests continue to pass.
- Code duplication is eliminated.

## Code Snippet (Duplicate Logic)

```python
# From GeminiKeyRotator.next_key
self._exhausted_keys.add(self.current_key)
available = [k for k in self.api_keys if k not in self._exhausted_keys]

if not available:
    logger.warning("[KeyRotator] All API keys exhausted")
    return None

# Find next available key
for i in range(len(self.api_keys)):
    next_idx = (self.current_idx + 1 + i) % len(self.api_keys)
    if self.api_keys[next_idx] not in self._exhausted_keys:
        self.current_idx = next_idx
        # ...
        return self.current_key
```
