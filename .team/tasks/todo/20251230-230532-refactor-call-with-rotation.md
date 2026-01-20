---
id: "20251230-230532-refactor-call-with-rotation"
status: todo
title: "Refactor complex `call_with_rotation` method in `ModelKeyRotator`"
created_at: "2025-12-30T23:05:32Z"
target_module: "src/egregora/llm/providers/model_key_rotator.py"
assigned_persona: "refactor"
---

## Description

The `call_with_rotation` method in the `ModelKeyRotator` class is overly complex and difficult to follow. Its high cyclomatic complexity makes it hard to test and maintain. The method should be broken down into smaller, more focused functions to improve readability and reduce complexity.

## Context

Complex methods are a common source of bugs and a significant barrier to understanding the codebase. Refactoring this method will improve the overall quality of the `llm/providers` module.

## Code Snippet

```python
# TODO: [Taskmaster] Refactor complex `call_with_rotation` method
# This method is too long and has a high cyclomatic complexity.
# It should be broken down into smaller, more manageable functions
# to improve readability and maintainability.
def call_with_rotation(
    self,
    call_fn: Callable[[str, str], Any],
    is_rate_limit_error: Callable[[Exception], bool] | None = None,
) -> Any:
    # ... method implementation ...
```
