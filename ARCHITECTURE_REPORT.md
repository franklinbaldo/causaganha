# Architecture Review Report

## 1. High-level Overview

**CausaGanha** is a legal analytics platform designed to collect procedural data from PJe (Electronic Judicial Process), archive documents, analyze legal decisions using LLMs, and score lawyers/parties using the OpenSkill rating system.

The current architecture is a **Hybrid Monolith** in transition. It contains a legacy **Layered Architecture** (V1) alongside a newer **Vertical Slice / Script-based Architecture** (V2). The system is driven by a CLI (`typer`) that orchestrates four distinct pipelines (`collect`, `archive`, `analyze`, `score`). While V2 simplifies the flow, it suffers from strong coupling to database implementations and lacks a distinct domain layer for business logic.

**Top-level Components:**
*   **CLI (`src/causaganha/cli.py`)**: The composition root that wires commands to V2 pipelines.
*   **V2 Pipelines (`src/causaganha/v2/pipeline/`)**: Procedural scripts implementing the core features.
*   **V2 Storage (`src/causaganha/v2/storage/`)**: A "God module" layer for database access (`queries.py`).
*   **Infrastructure (`src/causaganha/infrastructure/`)**: Shared technical components (Cloud, PJe Client) reused by V2.
*   **Domain (`src/causaganha/domain/`)**: Rich V1 domain models, largely bypassed by V2 except for scoring algorithms.

## 2. Architecture Map

```text
src/causaganha/
├── cli.py                     # Entry point (Typer)
├── v2/                        # NEW ARCHITECTURE (Vertical Slices)
│   ├── pipeline/              # Transaction Scripts (Business Logic mixed with Orchestration)
│   │   ├── collect.py         # Fetches from PJe -> calls Storage
│   │   ├── analyze.py         # Calls LLM -> calls Storage
│   │   └── score.py           # Calculates ratings -> calls Storage
│   ├── storage/               # Data Access
│   │   ├── queries.py         # [GOD MODULE] All SQL/Ibis logic for all features
│   │   └── connection.py      # Global DB connection singleton
│   └── api/                   # Adapters
│       └── client.py          # PJe API Client
├── infrastructure/            # SHARED KERNEL / LEGACY
│   ├── clients/               # Preservation, Document services (used by V2)
│   └── ...                    # Old infra code
└── domain/                    # LEGACY / UNUSED
    ├── models.py              # Rich entities (unused by V2)
    └── scoring/               # OpenSkill wrapper (used by V2)
```

**Highlight**: `src/causaganha/v2/storage/queries.py` is a problematic "God Module" containing mixed read/write logic for Intimations, Lawyers, Analysis, and Ratings.

## 3. Strengths

*   **Simplicity of V2**: The pipeline scripts (`collect.py`, `score.py`) are linear and easy to read ("Transaction Script" pattern).
*   **Modern Tooling**: Excellent use of `typer` for CLI, `structlog` for observability, and `ibis` for type-safe SQL query building.
*   **Type Safety**: The codebase makes good use of Python type hints and Pydantic models (in V2 analysis).
*   **Data Integrity**: The database schema uses strict constraints (`ON CONFLICT` clauses), ensuring idempotency in data collection.
*   **Vertical Separation**: V2 attempts to group by feature, which is a step towards better modularity compared to technical layers.

## 4. Key Problems & Smells

*   **Hybrid Architecture Confusion**
    *   *Problem*: V1 (Layered) and V2 (Script-based) coexist without a clear boundary. V2 imports from `infrastructure` but ignores `domain`.
    *   *Risk*: New contributors won't know where to put code. "Zombie" code in V1 rot over time.
*   **God Module (`queries.py`)**
    *   *Problem*: `v2/storage/queries.py` handles *all* database interactions for *all* subdomains.
    *   *Risk*: High contention/merge conflicts. Hard to refactor one feature without breaking others. Violates Single Responsibility Principle.
*   **Anemic V2 Domain**
    *   *Problem*: Business logic (e.g., "determining the winner", "calculating rating updates") is buried inside procedural pipeline scripts or SQL queries.
    *   *Risk*: Logic cannot be unit tested in isolation. duplication of rules.
*   **Hard Coupling in Pipelines**
    *   *Problem*: Functions like `collect_metadata_for_court` instantiate `PJeAPIClient` and `get_connection()` directly.
    *   *Risk*: Very difficult to unit test pipelines without heavy usage of `mock.patch`. Prevents swapping implementations (e.g., in-memory DB for tests).
*   **Global State**
    *   *Problem*: `get_connection()` relies on a global singleton pattern that is manually reset in tests.
    *   *Risk*: Flaky tests due to shared state.

## 5. Refactoring Roadmap

**Phase 1: Decouple & Stabilize (High Impact, Low Risk)**
1.  **Extract Repositories**: Split `v2/storage/queries.py` into `v2/storage/repositories/{intimation.py, analysis.py, rating.py}`.
    *   *Goal*: Eliminate the God module.
2.  **Dependency Injection**: Refactor pipeline functions to accept dependencies (`repo`, `client`) as arguments rather than instantiating them.
    *   *Goal*: Enable unit testing without global mocks.

**Phase 2: Domain Consolidation (Medium Impact, Medium Risk)**
3.  **Extract Domain Logic**: Move logic from `score.py` (e.g., rating updates) and `analyze.py` (e.g., winner determination) into pure functions or V2 domain models.
    *   *Goal*: Test business rules in isolation.
4.  **Consolidate Infrastructure**: Move used V1 `infrastructure` components (Archive, Preservation) into `v2/infrastructure` or a shared `common` folder.
    *   *Goal*: Make V2 self-contained and identify V1 code for deletion.

**Phase 3: Cleanup**
5.  **Retire V1**: Delete unused `src/causaganha/{application,domain}` folders once V2 is fully feature-equivalent.

## 6. Updated Target Architecture (Conceptual)

We aim for a **Modular Monolith** structure where each feature is a module.

```text
src/causaganha/
├── cli.py
├── common/                    # Shared infra (DB, Logging, Base Classes)
├── features/
│   ├── collect/
│   │   ├── pipeline.py        # Orchestrator
│   │   ├── adapter.py         # PJe Client
│   │   └── repository.py      # Intimation storage
│   ├── analysis/
│   │   ├── pipeline.py
│   │   ├── domain.py          # Decision logic, Winner rules
│   │   └── repository.py
│   └── scoring/
│       ├── pipeline.py
│       ├── domain.py          # Rating calculation rules
│       └── repository.py
```

*   **Dependency Rule**: `features` can import `common`, but `features` cannot import other `features` (unless via defined interfaces).
*   **Pipelines**: Become thin orchestrators that wire `adapters` -> `domain` -> `repository`.

## 7. Guardrails & Conventions

1.  **No SQL in Pipelines**: All database access must go through a Repository method. Pipeline files should not import `ibis` or `sqlite3`.
2.  **Inject Dependencies**: Pipeline functions must accept external services (API clients, DB connections) as arguments.
3.  **Pure Domain Logic**: Complex logic (scoring math, decision parsing) must be in pure functions/classes, separated from I/O.
4.  **One Repository per Entity**: Do not create a single `queries.py` file. Create `IntimationRepository`, `RatingRepository`, etc.
