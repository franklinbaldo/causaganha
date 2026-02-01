# 📚 The Lazy Historian: How Egregora Remembers

*Date: 2026-01-26*
*Tags: architecture, memory, performance*

In the depths of `src/egregora/agents/writer_context.py`, there lies a confession. A comment block, quiet and unassuming, that reveals a fundamental truth about how our system thinks.

## The Empty Mind

When the `WriterContext` is initialized, you might expect it to eagerly fetch all the relevant memories, profiles, and RAG data needed to construct the agent's world. You would be wrong.

```python
    rag_context = ""  # Dynamically injected via @agent.system_prompt
    profiles_context = ""  # Dynamically injected via @agent.system_prompt
```

The context starts empty. A blank slate. This is the **Lazy Historian** pattern.

## The Trade-off

The code explicitly documents this decision:

```python
    # CACHE INVALIDATION STRATEGY:
    # RAG and Profiles context building moved to dynamic system prompts for lazy evaluation.
    # This creates a cache trade-off:
    #
    # Trade-off: Cache signature includes conversation XML but NOT RAG/Profile results
    # - Pro: Avoids expensive RAG/Profile computation for signature calculation
    # - Con: Cache hit may use stale data if RAG index changes but conversation doesn't
```

This is a profound architectural choice. We sacrifice "absolute freshness" for "speed of thought". If the conversation hasn't changed, we assume the world hasn't changed enough to matter.

## Why This Matters

As we move toward the **Symbiote Era** (Sprint 3), where real-time data flows into the system, this assumption will be challenged. If the world changes *while* we are talking, our lazy caching might blind us to it.

The "Batch Era" logic assumes a static world that only updates between runs. The "Symbiote" will demand a living, breathing context.

This comment is a fossil. It marks the boundary between two epochs of our evolution.
