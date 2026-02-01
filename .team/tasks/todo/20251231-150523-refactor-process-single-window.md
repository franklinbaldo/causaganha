---
id: 20251231-150523-refactor-process-single-window
status: todo
title: "Refactor Complex _process_single_window Method"
created_at: "2025-12-31T15:05:23Z"
target_module: "src/egregora/orchestration/runner.py"
assigned_persona: "artisan"
---

## 📋 Refactor Complex `_process_single_window` Method

**Context:**
The `_process_single_window` method in `src/egregora/orchestration/runner.py` has grown too large and complex. It currently handles multiple responsibilities, including media processing, data enrichment, command handling, post generation, and profile creation. This violates the Single Responsibility Principle and makes the method difficult to read, test, and maintain.

**Task:**
Refactor the `_process_single_window` method by breaking it down into smaller, more focused private methods. Each new method should handle a distinct part of the process.

**Suggested Breakdown:**
- A method for media processing.
- A method for data enrichment.
- A method for handling commands and announcements.
- A method for generating posts.
- A method for generating profiles.

**Code Snippet:**
```python
def _process_single_window(self, window: Any, *, depth: int = 0) -> dict[str, dict[str, list[str]]]:
    # TODO: [Taskmaster] Refactor this method to reduce its complexity.
    """Process a single window with media extraction, enrichment, and post writing."""
    indent = "  " * depth
    window_label = f\"{window.start_time:%Y-%m-%d %H:%M} to {window.end_time:%H:%M}\"

    logger.info(\"%s➡️  [bold]%s[/] — %s messages (depth=%d)\", indent, window_label, window.size, depth)

    output_sink = self.context.output_format
    if output_sink is None:
        raise OutputSinkError(\"Output adapter must be initialized before processing windows.\")

    # ... and so on ...
```

**Acceptance Criteria:**
- The `_process_single_window` method is significantly shorter and acts as a coordinator for other private methods.
- The core logic is extracted into well-named, single-purpose methods.
- Existing tests continue to pass, or are updated to reflect the new structure.
