---
id: 20251231-150603-externalize-runner-config
status: todo
title: "Externalize Hardcoded Configuration in PipelineRunner"
created_at: "2025-12-31T15:06:03Z"
target_module: "src/egregora/orchestration/runner.py"
assigned_persona: "refactor"
---

## 📋 Externalize Hardcoded Configuration in PipelineRunner

**Context:**
The `_calculate_max_window_size` method in `src/egregora/orchestration/runner.py` contains hardcoded values for `avg_tokens_per_message` and `buffer_ratio`. These values are used to estimate the maximum number of messages that can fit into the language model's context window.

Hardcoding these values makes them difficult to adjust and fine-tune without modifying the source code. They should be moved to the application's configuration to allow for easier management.

**Task:**
1.  Move the hardcoded values (`avg_tokens_per_message` and `buffer_ratio`) from the `_calculate_max_window_size` method to a relevant configuration file.
2.  Update the method to read these values from the configuration.
3.  Ensure that default values are provided if the configuration settings are not present.

**Code Snippet:**
```python
def _calculate_max_window_size(self) -> int:
    """Calculate maximum window size based on LLM context window."""
    max_tokens = self._resolve_context_token_limit()
    # TODO: [Taskmaster] Externalize hardcoded configuration values.
    avg_tokens_per_message = 5
    buffer_ratio = 0.8
    return int((max_tokens * buffer_ratio) / avg_tokens_per_message)
```

**Acceptance Criteria:**
- The hardcoded values are removed from `_calculate_max_window_size`.
- The values are now read from the application's configuration.
- The application functions correctly with the new configuration-based approach.
