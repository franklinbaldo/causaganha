# Architecture Review Report

## 1. High-level Overview

**Purpose**: `causaganha` is a Judicial Analysis Platform designed to collect legal proceedings (intimations), archive documents, analyze decisions using AI (LLM/RAG), and score lawyer performance using skill rating systems.

**Current Architecture**: The system is currently a **Hybrid Monolith** in transition. It contains a legacy V1 layer (structured with `application`/`domain`/`infrastructure` layers) and a dominant V2 layer (structured as a "Vertical Slice" or "Pipeline-based" architecture). The V2 architecture relies heavily on script-like pipelines orchestrated via a CLI, with direct coupling to infrastructure and storage.

**Top-level Components**:
- **CLI (`src/causaganha/cli.py`)**: The central entry point and composition root that stitches V1 and V2 components together.
- **V2 Pipelines (`src/causaganha/v2/pipeline/`)**: The core workflow engines (`collect`, `archive`, `analyze`, `score`).
- **V2 Storage (`src/causaganha/v2/storage/`)**: A centralized module handling database connections and all data access logic (DuckDB/Ibis).
- **Domain (`src/causaganha/domain/`)**: Contains shared kernels (like `openskill` scoring) and V1 domain models.
- **Infrastructure (`src/causaganha/infrastructure/`)**: Houses V1 clients and cloud integrations.

## 2. Architecture Map

```text
src/causaganha/
├── cli.py                    # [Hub] Composition Root & Entry Point
├── v2/
│   ├── pipeline/             # [Orchestrators] Transaction scripts for main flows
│   │   ├── collect.py        # Fetches data from PJe
│   │   ├── analyze.py        # Runs LLM/RAG analysis
│   │   ├── score.py          # Updates lawyer ratings
│   │   └── archive.py        # [Best Practice] Uses DI for services
│   ├── storage/
│   │   ├── queries.py        # [God Module] Mixed data access & logic
│   │   └── schema.sql        # Database definitions
│   ├── api/
│   │   └── client.py         # [Infra] PJe API Client (HTTP)
│   └── analysis/             # [Domain/Infra] LLM & RAG implementations
├── domain/
│   ├── scoring/              # [Core] OpenSkill logic (Pure Domain)
│   └── models.py             # [Legacy] V1 Entities
├── infrastructure/
│   ├── clients/              # [Infra] V1 Document/Archive clients
│   └── integrations/         # [Infra] External service adapters
└── application/              # [Legacy] V1 Services
```

## 3. Strengths

- **Clear Pipeline Separation**: The division into `collect`, `archive`, `analyze`, and `score` provides a clear mental model of the data flow.
- **Shared Kernel Quality**: The `domain.scoring` module is a good example of a pure domain component—it encapsulates complex math (OpenSkill) without dependencies on DB or HTTP.
- **Strong Validation**: V2 uses `pydantic` heavily (e.g., `Intimation` models, `DecisionAnalysis`), ensuring data integrity at the edges.
- **Dependency Injection Emergence**: The `archive_documents` pipeline accepts `DocumentService` and `ArchiveService` as arguments, demonstrating a move towards better testability.
- **Comprehensive CLI**: The `typer` CLI effectively exposes all capabilities and handles the "wiring" of components (though some wiring is hardcoded deeper).
- **Parameterized Queries**: Despite being in a "God Module", raw SQL execution uses parameterized queries (`?`), preventing SQL injection.

## 4. Key Problems & Smells

*   **God Module `queries.py`**
    *   *Issue*: `src/causaganha/v2/storage/queries.py` contains ALL data access logic, business rules (e.g., how to calculate win rate), and serialization code.
    *   *Risk*: High coupling. A change in the database schema forces changes in this one massive file, causing merge conflicts. Hard to test individual queries in isolation.

*   **Tight Coupling in Pipelines**
    *   *Issue*: Pipelines like `collect.py` and `score.py` directly instantiate `get_connection()` and `PJeAPIClient`.
    *   *Risk*: Makes unit testing difficult (requires complex patching of globals or modules). Prevents easy swapping of implementations (e.g., for a different database or API mock).

*   **Split Infrastructure Personality**
    *   *Issue*: HTTP clients exist in both `src/causaganha/infrastructure/clients/` (V1) and `src/causaganha/v2/api/` (V2).
    *   *Risk*: Confusing discoverability. "Where do I add a new client?" is ambiguous. Duplication of HTTP client configuration (timeouts, headers).

*   **Implicit Domain Logic**
    *   *Issue*: Business rules (e.g., "What counts as a win?", "How is a rating updated?") are buried inside `queries.py` or pipeline scripts rather than in `domain` models.
    *   *Risk*: Logic cannot be reused or tested in isolation. The "Domain" is anaemic.

*   **Testing Fragmentation**
    *   *Issue*: Parallel test structures (`tests/unit` vs `tests/v2/unit`) and fixture duplication.
    *   *Risk*: Maintenance burden. New contributors might write tests in the wrong place or miss existing helpers.

## 5. Refactoring Roadmap

**Phase 1: Consolidate Infrastructure**
*   **Move V2 Client**: Move `src/causaganha/v2/api/client.py` to `src/causaganha/infrastructure/integrations/pje/client.py`.
*   **Goal**: Centralize all external I/O adapters in `infrastructure`.
*   **How**: Move file, update imports.

**Phase 2: Extract Repositories from God Module**
*   **Break `queries.py`**: Extract explicit repository classes to `src/causaganha/infrastructure/repositories/`.
    *   `IntimationRepository`: `store_intimations`, `get_unanalyzed_intimations`
    *   `AnalysisRepository`: `store_analysis`, `get_unrated_analyses`
    *   `RatingRepository`: `get_lawyer_rating`, `update_lawyer_rating`
*   **Goal**: Apply Single Responsibility Principle to data access.
*   **How**: Create classes that take a DB connection in `__init__`. Move methods from `queries.py` to these classes.

**Phase 3: Inject Dependencies into Pipelines**
*   **Refactor Pipelines**: Change pipeline functions (`collect_metadata_for_all_courts`, `calculate_ratings`) to accept Repositories and Clients as arguments.
*   **Goal**: Enable true unit testing and dependency inversion.
*   **How**: Update function signatures. Update `cli.py` to instantiate repositories/clients and pass them in.

**Phase 4: Enrich Domain Model**
*   **Extract Logic**: Move rating calculation logic (e.g., win rate math) from `queries.py`/Repositories into `domain` entities or services.
*   **Goal**: Pure Python business logic that is easy to test.
*   **How**: Create `LawyerRating` domain entity with methods like `update_rating(outcome)`.

## 6. Updated Target Architecture (Conceptual)

This architecture adopts a **Modular Monolith** approach with **Dependency Injection**.

*   **`cli/`** (Presentation): Handles user input, wires dependencies (Composition Root).
*   **`pipeline/`** (Application Services): Orchestrates flows.
    *   *Imports*: `domain`, `infrastructure` (via interfaces/injection).
    *   *Responsibility*: "Get data from A, process with B, save to C".
*   **`domain/`** (Core): Entities, Value Objects, Pure Logic.
    *   *Imports*: None (Standard Library only).
    *   *Responsibility*: "Calculate score", "Validate decision".
*   **`infrastructure/`** (Adapters): DB access, API clients.
    *   *Imports*: `domain`.
    *   *Responsibility*: Implement Repositories, call APIs.
    *   *Submodules*: `repositories/`, `clients/`, `database/`.

**Benefits**:
- **Testability**: Pipelines can be tested with mock repositories. Domain logic can be tested with unit tests.
- **Maintainability**: DB schema changes only affect Repositories.
- **Clarity**: "API" means "our API", "Client" means "external API".

## 7. Guardrails & Conventions

1.  **No Logic in Infrastructure**: Repositories should only save/load data. They should not calculate business values (like ratings).
2.  **Pipelines are Orchestrators**: Pipelines should not contain SQL or raw HTTP calls. They delegate to Repositories and Clients.
3.  **Inject, Don't Import**: Avoid `get_connection()` inside functions. Pass the connection (or better, the Repository) as an argument.
4.  **Domain is Pure**: Domain files must not import `ibis`, `duckdb`, or `httpx`.
5.  **One Way Dependencies**: `Domain` <- `Infrastructure` <- `Pipeline` <- `CLI`.
