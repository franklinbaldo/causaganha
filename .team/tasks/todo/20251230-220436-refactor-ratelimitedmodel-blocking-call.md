---
id: 20251230-220436-refactor-ratelimitedmodel-blocking-call
status: todo
title: "Refactor RateLimitedModel to Handle Blocking Calls in Async Methods"
created_at: "2025-12-30T22:04:36Z"
target_module: "src/egregora/llm/providers/rate_limited.py"
assigned_persona: "artisan"
---

## Description

The `RateLimitedModel.request` method is an `async` function that contains a synchronous, blocking call: `limiter.acquire()`. This is a dangerous practice in asynchronous code as it can block the entire event loop, leading to performance degradation or deadlocks.

The task is to refactor this method to ensure the blocking call is handled safely without blocking the event loop.

## Context

The existing comments in the code indicate awareness of the problem but leave it unresolved. A proper solution would likely involve running the blocking `acquire` and `release` calls in a separate thread using `asyncio.to_thread` or a similar mechanism.

## Code Snippet

```python
# src/egregora/llm/providers/rate_limited.py

class RateLimitedModel(Model):
    # ...
    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        """Make a rate-limited request."""
        limiter = get_rate_limiter()

        # ... comments about blocking ...

        # TODO: [Taskmaster] Refactor to safely handle blocking call in async method
        limiter.acquire()
        try:
            return await self.wrapped_model.request(messages, model_settings, model_request_parameters)
        finally:
            limiter.release()
```
