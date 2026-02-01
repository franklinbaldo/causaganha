---
id: 20251231-090749-extract-command-processing
status: todo
title: "Extract Command Processing Logic from _process_single_window"
created_at: "2025-12-31T09:07:49Z"
target_module: "src/egregora/orchestration/runner.py"
assigned_persona: "artisan"
---

### Description

As part of the decomposition of the `_process_single_window` method, the logic for handling commands needs to be extracted into its own method.

### Task

1.  Implement the `_process_commands` method to handle command extraction and processing.
2.  Update `_process_single_window` to use this new method.
3.  Remove the `# TODO` comment from `_process_commands` after implementation.

### Code Snippet
```python
# src/egregora/orchestration/runner.py

# ...
    # TODO: [Taskmaster] Extract command processing logic from _process_single_window
    def _process_commands(self, messages_list: list[dict], output_sink: Any) -> int:
        """Processes commands from a list of messages."""
# ...
```
