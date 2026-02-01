# 🏛️ Architecture: The Batch Era

**Status:** Current (Sprint 1-2)
**Next Epoch:** [The Symbiote Era](Architecture-Symbiote-Era.md)

## Overview
The **Batch Era** describes the architectural state of the system where **Egregora** operates as a discrete, scheduled command-line interface (CLI) tool. In this era, the system wakes up, performs a batch of work, and shuts down. It has no persistent memory in RAM; all state is persisted to disk (databases, markdown files) between runs.

## Core Characteristics

### 1. CLI-Driven Execution
The entry point is a CLI command (`egregora write`, `egregora demo`).
- **Trigger:** Manual invocation or CRON scheduler.
- **Lifecycle:** Process start -> Load Config -> Execute Pipeline -> Process Exit.
- **Consequence:** High latency for "first byte", but very robust and easy to debug.

### 2. Recursive Task Splitting
The heart of the execution engine (`runner.py`) uses a recursive strategy to handle work.
- It breaks large time windows into smaller chunks.
- It continues splitting until a chunk fits within the token context window.
- **Philosophy:** "Divide and Conquer" rather than "Stream and Process".

### 3. Lazy Context Loading
As documented in [The Lazy Historian](../personas/lore/blog/002-the-lazy-historian.md), the system optimizes for cache hits by lazily loading RAG and Profile data.
- **Assumption:** The world is static during the execution of a single batch.

### 4. Static Output
The primary output is a static site (MkDocs).
- **Feedback Loop:** Long. Users see changes only after the next build/deploy cycle.

## Historical Significance
This architecture was essential for bootstrapping the system. It allowed for:
- **Simplicity:** No complex async servers or event loops (initially).
- **Stability:** "Crash-only software" principles applies; if it fails, just run it again.

## The Coming Shift
As of Sprint 2, the **Visionary** and **Simplifier** are steering the system toward the **Symbiote Era**: a real-time, event-driven architecture that lives alongside the user. This will require dismantling the "Batch" assumptions, particularly the static context loading.
