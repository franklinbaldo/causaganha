---
id: "20251230-230532-remove-redundant-factory"
status: todo
title: "Remove redundant `create_model_key_rotator` function"
created_at: "2025-12-30T23:05:32Z"
target_module: "src/egregora/llm/providers/model_key_rotator.py"
assigned_persona: "absolutist"
---

## Description

The `create_model_key_rotator` factory function is a thin wrapper around the `ModelKeyRotator` constructor and provides no additional value. It should be removed to simplify the API, and direct instantiation of the `ModelKeyRotator` class should be used instead.

## Context

Unnecessary abstractions add complexity to the codebase without providing any tangible benefits. Removing this function will make the code easier to understand and maintain.

## Code Snippet

```python
# TODO: [Taskmaster] Remove redundant `create_model_key_rotator` function
# This factory function is a thin wrapper around the ModelKeyRotator constructor
# and does not provide any additional value. It should be removed to simplify
# the API. Direct instantiation of the class should be used instead.
def create_model_key_rotator(
    models: list[str] | None = None,
    api_keys: list[str] | None = None,
) -> ModelKeyRotator:
    """Create a combined model+key rotator."""
    return ModelKeyRotator(models=models, api_keys=api_keys)
```
