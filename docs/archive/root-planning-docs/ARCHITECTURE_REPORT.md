# Architecture Review Report

## 1. High-level Overview

**Purpose:** The `causaganha` repository is an automated data pipeline designed to ingest judicial decisions, analyze them using LLMs (Gemini) and RAG techniques, and rank lawyers based on their win rates using the OpenSkill algorithm.

**Current Architecture:** The system follows a **Pipeline-Centric Modular Monolith** or "Script-based" architecture. Functionality is vertically sliced by pipeline stage (Collection -> Analysis -> Scoring), orchestrated via a CLI. While effective for an MVP, it currently lacks a distinct domain layer, leading to business logic leaking into orchestration scripts and storage modules.

**Main Components:**
*   **CLI (`src/causaganha/cli`)**: The entry point for all operations, utilizing `Typer` to expose commands.
*   **Pipelines (`src/causaganha/pipeline`)**: The core orchestrators that tie together data collection, analysis, and storage. Currently, these modules contain significant business logic.
*   **Storage (`src/causaganha/storage`)**: Handles persistence using DuckDB. It currently mixes schema definitions, connection management, and raw SQL execution in a few large files.
*   **Analysis (`src/causaganha/analysis`)**: Encapsulates the logic for interacting with LLMs (Gemini) and RAG systems to classify judicial decisions.
*   **Clients (`src/causaganha/clients`)**: Adapters for external services like the PJe API and Internet Archive.
*   **Scoring (`src/causaganha/scoring`)**: Implements the ranking logic using the OpenSkill library.

## 2. Architecture Map

```text
src/causaganha/
├── cli/                 – Command-line interface entry points (Typer)
│   ├── commands/        – Specific command implementations (collect, analyze, db)
│   └── __init__.py      – App aggregation
├── pipeline/            – WORKFLOW ORCHESTRATION (God Modules)
│   ├── collect.py       – Data ingestion logic (mixes HTTP, Zip handling, DTO mapping)
│   ├── analyze.py       – Analysis workflow (batching, error handling, strategy selection)
│   └── archive.py       – Archival workflow logic
├── analysis/            – AI/ML DOMAIN LOGIC
│   ├── models.py        – Pydantic models for decision classification
│   ├── analyzer.py      – LLM interaction logic
│   └── rag_analyzer.py  – RAG specific implementation
├── clients/             – INFRASTRUCTURE ADAPTERS
│   ├── pje.py           – PJe API client
│   └── archive.py       – Internet Archive client
├── scoring/             – DOMAIN LOGIC
│   └── openskill.py     – Ranking algorithm wrappers
├── storage/             – PERSISTENCE LAYER
│   ├── connection.py    – DuckDB connection management
│   ├── schema.sql       – Database schema
│   └── queries.py       – DATA ACCESS OBJECT (God Object: Raw SQL + Logic)
└── config.py            – Application configuration (Pydantic Settings)
```

**Highlight:** `src/causaganha/storage/queries.py` acts as a "God Object" for data access, containing all SQL queries for the application, mixing read/write concerns, and leaking business logic (e.g., win-rate calculation).

## 3. Strengths

*   **Modern Python Stack:** The project utilizes modern Python features (3.11+), including extensive use of `asyncio` for I/O-bound tasks and type hinting throughout.
*   **Effective Data Stack:** The choice of **DuckDB** for local analytical processing is excellent for this scale, providing fast SQL capabilities without the overhead of a heavy server. **Pydantic** ensures strong data validation at boundaries.
*   **Clear Vertical Slices:** The pipeline structure (`collect` -> `analyze` -> `score`) is intuitive and maps directly to the user's mental model of the workflow.
*   **CLI UX:** The use of **Typer** results in a clean, discoverable, and well-structured command-line interface.
*   **AI Integration:** The `analysis` module shows a good separation of concerns regarding the specific AI strategy (LLM vs. RAG vs. Hybrid), abstracting some of the complexity of the underlying models.

## 4. Key Problems & Smells

*   **God Object in Storage (`queries.py`)**
    *   *Problem:* A single file contains all SQL logic for the entire application. It mixes unrelated domains (Intimations, Lawyers, Ratings).
    *   *Risk:* High merge conflict risk, poor discoverability, and difficult to refactor. It encourages tight coupling between unrelated parts of the system.
*   **Raw SQL & Logic Leakage in Storage**
    *   *Problem:* `queries.py` uses raw SQL strings (`con.con.execute`) mixed with Ibis expressions. Business logic (like calculating win rates) is embedded within the persistence functions.
    *   *Risk:* Testing business logic requires a database; changing the storage backend (e.g., to Postgres) would be a massive rewrite.
*   **Pipelines doing too much (Orchestration + Logic)**
    *   *Problem:* `pipeline/collect.py` handles HTTP requests, ZIP file extraction, JSON parsing, DTO mapping, and error recovery all in one function.
    *   *Risk:* Hard to unit test. Testing "collection" requires mocking the entire world (Network, Zip, DB). It violates the Single Responsibility Principle.
*   **Anemic Domain Model**
    *   *Problem:* While `analysis/models.py` exists, much of the system passes around `dict`s, `SimpleNamespace`, or raw tuples. There is no central "Domain" layer defining what an `Intimation` or `Lawyer` *is* independent of the database or API.
    *   *Risk:* Inconsistent data structures across the app. "Shotgun surgery" is required when a core concept changes.
*   **Implicit Dependency Coupling**
    *   *Problem:* Pipelines import specific implementation details from `storage` and `clients`.
    *   *Risk:* Cannot easily swap implementations (e.g., for testing or different environments).

## 5. Refactoring Roadmap

This roadmap focuses on extracting a proper Layered Architecture from the current scripts.

**Step 1: Extract Repositories (The "Storage" Cleanup)**
*   **Scope:** `src/causaganha/storage/`
*   **Goal:** Break `queries.py` into distinct repository classes.
*   **Plan:**
    *   Create `src/causaganha/storage/repositories/`.
    *   Create `IntimationRepository`, `LawyerRepository`, `AnalysisRepository`.
    *   Move functions from `queries.py` to methods in these classes.
    *   Update `queries.py` to re-export or deprecate these functions.

**Step 2: Define Domain Entities**
*   **Scope:** `src/causaganha/domain/`
*   **Goal:** Create a source of truth for data structures.
*   **Plan:**
    *   Create `src/causaganha/domain/models.py`.
    *   Define Pydantic models for `Intimation`, `Lawyer`, `Decision`, `Rating` that are storage-agnostic.
    *   Update Repositories to accept/return these models instead of dicts/tuples.

**Step 3: Extract Services (The "Logic" Cleanup)**
*   **Scope:** `src/causaganha/services/` & `src/causaganha/pipeline/`
*   **Goal:** Move business logic out of pipelines.
*   **Plan:**
    *   Create `CollectionService`: Handle the logic of fetching, unzipping, and parsing from `pipeline/collect.py`.
    *   Create `AnalysisService`: Encapsulate the strategy selection and batch processing from `pipeline/analyze.py`.
    *   Create `RankingService`: Encapsulate the OpenSkill logic.
    *   Pipelines become thin orchestrators calling these services.

**Step 4: Introduce Dependency Injection**
*   **Scope:** Global
*   **Goal:** Decouple components for better testability.
*   **Plan:**
    *   Pass `Repository` instances into `Service` constructors.
    *   Pass `Service` instances into Pipeline functions (or use a simple container/factory).

## 6. Updated Target Architecture (Conceptual)

**Layered Architecture:**

1.  **Presentation Layer (`cli/`)**:
    *   Handles user input/output.
    *   Calls Application Services.
    *   *Dependencies:* Depends on Services.

2.  **Application Service Layer (`services/`)**:
    *   Orchestrates domain logic.
    *   "Download data", "Analyze batch", "Rank lawyers".
    *   *Dependencies:* Depends on Domain and Repository Interfaces.

3.  **Domain Layer (`domain/`)**:
    *   Core entities (`Intimation`, `Lawyer`).
    *   Pure Python/Pydantic.
    *   *Dependencies:* **Zero dependencies** on outer layers.

4.  **Infrastructure Layer (`storage/`, `clients/`)**:
    *   **Repositories:** Implement data access (DuckDB).
    *   **Clients:** Implement external API access (PJe, Archive).
    *   *Dependencies:* Depends on Domain (to map data).

**Cross-cutting concerns:**
*   **Configuration:** Handled via `pydantic-settings` (already in place).
*   **Logging:** `structlog` (already in place) injected or imported globally.

## 7. Guardrails & Conventions

*   **No Raw SQL in Logic Layers:** All SQL must reside strictly within `src/causaganha/storage/repositories/`. Services and Pipelines must never see SQL.
*   **Pipelines are Orchestrators:** Pipelines should only call Services. They should not contain `if/else` logic related to business rules (e.g., "if win_rate > 0.5").
*   **Domain Models are the Currency:** Data passed between layers must be Domain Models (Pydantic), not `dict` or `tuple`.
*   **Repositories Return Entities:** Repositories must map database rows to Domain Models before returning them.
*   **New Integrations:** Any new external API integration must have a dedicated client class in `clients/` and be used via a Service.
