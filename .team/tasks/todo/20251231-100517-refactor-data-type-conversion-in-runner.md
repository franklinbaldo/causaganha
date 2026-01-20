---
id: 20251231-100517-refactor-data-type-conversion-in-runner
status: todo
title: "Refactor data type conversion for consistency"
created_at: "2025-12-31T10:05:17Z"
target_module: "src/egregora/orchestration/runner.py"
assigned_persona: "refactor"
---

## Description

The `_process_single_window` method in `PipelineRunner` contains a complex `try-except` block to handle the conversion of `enriched_table` to a list. This suggests that the data type being passed is inconsistent, making the code brittle and hard to maintain.

## Task

Refactor the data pipeline to ensure a consistent data type is always passed, removing the need for the multi-layered `try-except` block. This will improve code clarity and robustness.

## Code Snippet

```python
        # Convert table to list for command processing
        try:
            messages_list = enriched_table.execute().to_pylist()
        except (AttributeError, TypeError):
            try:
                messages_list = enriched_table.to_pylist()
            except (AttributeError, TypeError):
                messages_list = enriched_table if isinstance(enriched_table, list) else []
```
