---
id: 20251231-090718-refactor-magic-number-for-token-limit
status: todo
title: "Refactor Magic Number for Token Limit"
created_at: "2025-12-31T09:07:18Z"
target_module: "src/egregora/orchestration/runner.py"
assigned_persona: "refactor"
---

### Description

The `_resolve_context_token_limit` method in `PipelineRunner` uses a hardcoded magic number (`1_048_576`) which has been aliased to a constant but the refactor is not complete. This makes the code harder to read and maintain.

### Task

1.  Replace the magic number with the existing named constant `FULL_CONTEXT_WINDOW_SIZE`.
2.  Remove the `# TODO` comment after the refactoring is complete.

### Code Snippet
```python
# src/egregora/orchestration/runner.py

# ...
    def _resolve_context_token_limit(self) -> int:
        """Resolve the effective context window token limit."""
        config = self.context.config
        use_full_window = getattr(config.pipeline, "use_full_context_window", False)

        # TODO: [Taskmaster] Refactor magic number for token limit
        if use_full_window:
            return self.FULL_CONTEXT_WINDOW_SIZE

        return config.pipeline.max_prompt_tokens
# ...
```
