---
id: 20251231-090735-decompose-process-single-window
status: todo
title: "Decompose _process_single_window Method"
created_at: "2025-12-31T09:07:35Z"
target_module: "src/egregora/orchestration/runner.py"
assigned_persona: "refactor"
---

### Description

The `_process_single_window` method in `PipelineRunner` has grown too large and handles too many responsibilities, including command processing and status message generation. This complexity makes the method difficult to read, test, and maintain.

### Task

1.  Refactor the method by extracting the command processing logic into a new private method, `_process_commands`.
2.  Extract the status message construction into a new private method, `_construct_status_message`.
3.  Update `_process_single_window` to call these new methods.
4.  Remove the `# TODO` comment after the refactoring is complete.

### Code Snippet
```python
# src/egregora/orchestration/runner.py

# ...
    def _process_single_window(self, window: Any, *, depth: int = 0) -> dict[str, dict[str, list[str]]]:
        # TODO: [Taskmaster] Decompose _process_single_window method
        """Process a single window with media extraction, enrichment, and post writing."""
# ...
```
