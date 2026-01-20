---
id: 20251230-220507-refactor-modelkeyrotator-logic
status: todo
title: "Refactor ModelKeyRotator for Clarity and Simplified Logic"
created_at: "2025-12-30T22:05:07Z"
target_module: "src/egregora/llm/providers/model_key_rotator.py"
assigned_persona: "refactor"
---

## Description

The `ModelKeyRotator.call_with_rotation` method contains a `while True` loop with complex, nested control flow. The logic relies on multiple `continue` statements and checks to iterate through models and keys, making it difficult to understand and maintain.

The task is to refactor this method to make the iteration logic more explicit and easier to follow.

## Context

A clearer implementation might involve nested loops (e.g., `for model in models: for key in keys:`), which would make the control flow more straightforward and eliminate the need for the `while True` and multiple `continue` statements. This would improve the readability and long-term maintainability of the code.

## Code Snippet

```python
# src/egregora/llm/providers/model_key_rotator.py

class ModelKeyRotator:
    # ...
    def call_with_rotation(
        self,
        call_fn: Callable[[str, str], Any],
        is_rate_limit_error: Callable[[Exception], bool] | None = None,
    ) -> Any:
        # TODO: [Taskmaster] Refactor for clarity and simplified logic
        """Call function trying all keys for each model before rotating models."""
        # ...
        while True:
            # ... complex logic with multiple continue statements ...
```
