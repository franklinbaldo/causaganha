---
id: 20251231-090848-extract-status-message-generation
status: todo
title: "Extract Status Message Generation from _process_single_window"
created_at: "2025-12-31T09:08:48Z"
target_module: "src/egregora/orchestration/runner.py"
assigned_persona: "refactor"
---

### Description

As part of the decomposition of the `_process_single_window` method, the logic for generating the status message needs to be extracted into its own method.

### Task

1.  Implement the `_construct_status_message` method.
2.  Update `_process_single_window` to use this new method for logging.
3.  Remove the `# TODO` comment from `_construct_status_message` after implementation.

### Code Snippet
```python
# src/egregora/orchestration/runner.py

# ...
    # TODO: [Taskmaster] Extract status message generation from _process_single_window
    def _construct_status_message(
        self, posts: list, profiles: list, announcements_generated: int
    ) -> str:
        """Constructs a status message for logging."""
# ...
```
