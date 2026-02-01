# 🏛️ The Symbiote Era (Sprint 3+)

**Status:** Active
**Epoch:** 2026-01-29 — Present
**Key Theme:** Modularity, Resilience, Observability
**Trigger Event:** The Great Refactor (Commit `059be01` by `janitor`)

---

## 🌅 Introduction: The Machine Wakes Up

The **Symbiote Era** marks the transition of Egregora from a set of monolithic "Batch Era" scripts into a reactive, modular, and resilient system. The name "Symbiote" reflects the architectural goal: the system should not just be a tool the user fires and forgets, but a partner that maintains its own state, handles errors gracefully, and provides deep observability into its processes.

This era was precipitated by the [Architecture Analysis of Jan 2026](../wiki/Architecture.md), which identified that the complexity of the original `write.py` (1400+ lines) had become a liability.

## 🏗️ Architectural Pillars

### 1. Modular Pipelines
The monolithic `write.py` has been decomposed into distinct logical domains:

- **ETL (`orchestration/pipelines/etl/`)**: Handles data ingestion, preparation (`preparation.py`), and privacy filtering. It is purely functional and side-effect free where possible.
- **Coordination (`orchestration/pipelines/coordination/`)**: Manages background tasks (`background_tasks.py`), state persistence, and inter-process communication.
- **Execution (`write.py` logic)**: While originally planned as a separate module, the core processing loop currently resides within `write.py` (lines ~350+), acting as the central nervous system that binds ETL and Agents together.

### 2. Explicit Configuration
Gone are the "magic numbers" buried deep in conditional logic. The Symbiote architecture enforces explicit configuration via `src/egregora/config/defaults.py`.
- **Single Source of Truth**: All default values (rate limits, window sizes, model names) are centralized in `PipelineDefaults`, `ModelDefaults`, etc.
- **Overridability**: Defaults can be cleanly overridden by runtime configuration without code changes.

### 3. Unified State
The system manages state through a unified **`PipelineContext`** (`src/egregora/orchestration/context.py`) which splits concerns into:
- **`PipelineConfig`**: Immutable configuration and paths.
- **`PipelineState`**: Mutable runtime state (clients, connections, caches, task stores).

This allows the system to pass a single context object that provides access to everything needed for execution, ensuring consistency.

### 4. The Persistent Queue (TaskStore)
To ensure resilience against crashes and interruptions, the Symbiote employs a **[Persistent Task Store](Patterns-TaskStore.md)** pattern.
- **Mechanism**: A DuckDB-backed transactional queue (`tasks` table) that persists intent before execution.
- **Benefit**: If the pipeline fails, tasks remain pending. The system resumes exactly where it left off upon restart.
- **Observability**: Queue depth and failure rates are queryable via standard SQL.

### 5. Evaluation & Feedback (Elo)
The system has moved beyond simple generation to self-evaluation.
- **Elo Rating**: Posts are pitted against each other in pairwise comparisons.
- **Feedback Loops**: The Reader agent provides structured feedback (star ratings, critique) which persists in the database.
- **Darwinian Evolution**: Over time, higher quality content rises to the top of the "Top Posts" list.

### 6. Error Boundaries (Partial)
The "crash-on-first-error" pattern is being replaced. While a formal `ErrorBoundary` protocol is not yet fully implemented, the system now employs broad exception handling at the item processing level to prevent one bad window from crashing the entire pipeline.

## 🧩 Key Components

### The Orchestrator (`orchestration/`)
The brain of the system. It delegates:
- **`etl`**: Prepares the data.
- **`write.py`**: The coordinator that executes the processing loop, handles item isolation, and manages the lifecycle of the run.
- **`journal.py`**: Records execution history to prevent re-processing.

### The Agents (`agents/`)
Specialized workers that perform discrete cognitive tasks.
- **[Writer](Architecture-Writer-Agent.md)**: Converts chat windows into narrative posts. Implements the "Composition Root" pattern.
- **Reader**: Evaluates and ranks posts using an Elo rating system (`agents/reader/`).
- **Profile**: Updates author profiles based on new evidence.
- **Banner**: Generates visual assets for posts (Async via TaskStore).
- **Enricher**: Handles media and URL enrichment. Currently bifurcating into a monolithic worker (`enricher.py`) and specialized functional agents (`enrichment.py`).

### The Sinks (`output_sinks/`)
Pluggable destinations for the generated content. Currently focused on MkDocs, but architected to support Notion, SQL, or other CMSs in the future.

## ⚠️ Known Technical Debt (Lore)

### The Ghost Reclaimed (`write.py` consolidation)
Early in the Symbiote Era, an attempt was made to move execution logic to a dedicated `processor.py`. However, the complexity of distributed state management proved premature. The logic was consolidated back into `write.py`'s `process_item` function.
- **Status:** Consolidated. The "Ghost in the Shell" has become the Shell.
- **Lore:** The `[Taskmaster]` tag persists in comments as a reminder of the refactoring work that remains (e.g., validation logic, complexity reduction).

### The Illusion of Concurrency (`enricher.py`)
- **Status:** In Progress (Mitigation).
- **Lore:** The system attempts to scale enrichment concurrency based on the number of available API keys. The monolithic `enricher.py` suffered from thread-safety issues with key rotation.
- **Evolution:** The new `enrichment.py` module represents the first step in decomposing this monolith into smaller, stateless functional agents that are easier to scale and test.

## 📈 Evolution from Batch Era

| Feature | Batch Era (Sprint 1-2) | Symbiote Era (Sprint 3+) |
| :--- | :--- | :--- |
| **Structure** | Monolithic Scripts (`write.py`) | Modular Packages (`etl`) + Coordinator (`write.py`) |
| **Configuration** | Implicit / Magic Numbers | Explicit `defaults.py` |
| **Failure Mode** | Catastrophic Exit | Item-Level Isolation |
| **State** | Filesystem Artifacts | `PipelineContext` (In-Memory + Journal) |
| **Philosophy** | "Run this script" | "Manage this pipeline" |

## 🔮 Future Direction

The Symbiote Era lays the groundwork for:
- **Multi-Provider Support**: Seamlessly switching between Google Gemini, OpenAI, and Anthropic.
- **Dry-Run Mode**: Estimating costs and tokens before spending a dime.
- **Live Observability**: Real-time dashboards of pipeline progress.
- **Further Decomposition**: Eventually extracting `process_item` into a dedicated `ExecutionStrategy` pattern.
