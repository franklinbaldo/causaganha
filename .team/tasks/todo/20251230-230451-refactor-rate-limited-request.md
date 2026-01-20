---
id: "20251230-230451-refactor-rate-limited-request"
status: todo
title: "Refactor `request` method in `RateLimitedModel` for consistency"
created_at: "2025-12-30T23:04:51Z"
target_module: "src/egregora/llm/providers/rate_limited.py"
assigned_persona: "refactor"
---

## Description

The `request` method in the `RateLimitedModel` class should be refactored to use a `try...finally` block for releasing the rate limiter. This will make its implementation consistent with the `request_stream` method, improving code clarity and robustness.

## Context

The current implementation acquires the limiter and then immediately enters a `try...finally` block. While functional, it's less clean than the pattern used in `request_stream`, where the limiter is acquired *before* the `try` block.

## Code Snippet

```python
# TODO: [Taskmaster] Refactor to use a try...finally block for consistency
# The current implementation is inconsistent with `request_stream`.
# It should acquire the limiter and then use a `try...finally`
# block to ensure the limiter is always released.
limiter.acquire()
try:
    return await self.wrapped_model.request(messages, model_settings, model_request_parameters)
finally:
    limiter.release()
```
