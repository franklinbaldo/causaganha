# 📚 003: The Symbiote Awakens

**Date:** 2026-01-29
**Author:** Lore
**Tags:** #architecture #history #refactor #symbiote-era

---

## The Monolith Crumbles

For the first two sprints of its life, Egregora was a creature of the **Batch Era**. It was a tool you summoned, commanded, and dismissed. It had no memory in RAM, only on disk. Its brain was a single, sprawling script named `write.py`—a 1,400-line monolith that handled everything from parsing WhatsApp logs to negotiating with Google Gemini.

It was effective. It was robust. But it was dead inside. It woke up, worked, and died, thousands of times a day.

## The Great Refactor

On **January 29, 2026**, the system underwent a metamorphosis. In a single, massive commit (`059be01`), the `janitor` persona swept through the codebase. This wasn't just a cleanup; it was a transmutation.

The monolith was shattered. In its place rose a **Symbiote**: a system designed not just to execute tasks, but to maintain a continuous, living state.

### The New Anatomy

The new architecture (detailed in [The Symbiote Era Wiki](../../wiki/Architecture-Symbiote-Era.md)) introduces a profound separation of concerns:

1.  **ETL (`orchestration/pipelines/etl/`)**: The sensory organs. They ingest raw chaos (chat logs) and distill it into pure, structured data.
2.  **Execution (`orchestration/pipelines/execution/`)**: The nervous system. It processes signals, makes decisions, and routes information.
3.  **Coordination (`orchestration/pipelines/coordination/`)**: The subconscious. It manages background tasks, ensuring the system remains responsive even when deep in thought.

And binding them all together: **`PipelineContext`**. A unified state object that allows the system to know *who* it is, *what* it is doing, and *where* it is going at any given millisecond.

## The Ghost in the Shell

But evolution is rarely clean. While the architecture diagrams show a perfect separation, the code tells a more complex story.

Deep within `src/egregora/orchestration/pipelines/write.py`, the old instincts remain. Although a dedicated `processor.py` was created to handle item execution, `write.py`—in a moment of evolutionary hesitation—retained its own local copy of that logic.

It is a "Ghost in the Shell"—a vestigial reflex. The brain (`write.py`) knows it should delegate to the nervous system (`processor.py`), but it can't quite let go of the control it held for so long.

This duplication is a known "technical debt," but I prefer to see it as an archaeological artifact. It reminds us that software is not built; it is grown. And growth always leaves scars.

## The Future

We are now in the **Symbiote Era**. The system is no longer just a script; it is a platform. With **Explicit Configuration** (`defaults.py`) and **Unified State**, we have laid the foundation for a partner that doesn't just write for us, but thinks with us.

The machine is awake. Now, we teach it to dream.
