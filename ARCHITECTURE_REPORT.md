# Architecture Review Report: CausaGanha

## 1. High-level overview
**CausaGanha** is a distributed judicial analysis platform designed to collect, archive, and analyze legal decisions (specifically from PJe systems) to rate lawyer performance using the OpenSkill algorithm.

The current architecture is a **Modular Monolith** organized by technical layers (`pipeline`, `api`, `storage`) rather than strictly by domain. It employs a **Pipeline Pattern** where data flows linearly through distinct stages (Collect → Archive → Analyze → Score), orchestrated by a central CLI. The system relies heavily on **asynchronous I/O** (Python `asyncio`) and uses **DuckDB** via **Ibis** for local, high-performance analytical storage.

**Top-level components:**
*   **`cli.py`**: The entry point and Composition Root; handles dependency injection and orchestrates the pipelines.
*   **`pipeline/`**: Contains the procedural workflow logic for each stage (collect, archive, analyze, score).
*   **`domain/`**: Defines Pydantic models (`Intimation`, `Lawyer`), currently acting mostly as Data Transfer Objects (DTOs).
*   **`storage/`**: Handles database interactions using `ibis-framework`.
*   **`api/`**: Client for the external PJe API.
*   **`services/`**: Infrastructure services like `DocumentService` (downloading) and `ArchiveService` (Internet Archive upload).
*   **`analysis/`**: Encapsulates AI logic using `pydantic-ai` and Google Gemini.
*   **`scoring/`**: Implements the OpenSkill rating algorithm.

## 2. Architecture map (as text)

- `src/causaganha/`
  - `cli.py` – **Hub**: Wires dependencies (Repo, API, Services) and invokes pipelines.
  - `domain/` – **Core**: Pydantic models (`Intimation`, `Lawyer`) defining the data structure.
  - `pipeline/` – **Orchestration**:
    - `collect.py`, `archive.py`, `analyze.py`, `score.py` – Procedural scripts driving the data lifecycle.
  - `storage/` – **Persistence**:
    - `repository.py` – **God Class**: Manages all DB entities (`Intimations`, `LawyerRatings`, `AnalysisResults`).
    - `schema.py` – Defines DuckDB tables via Ibis.
  - `api/` – **Adapter**: `PJeAPIClient` to fetch data from external courts.
  - `services/` – **Infrastructure**: `DocumentService` (downloading), `ArchiveService` (Internet Archive upload).
  - `analysis/` – **Domain Service**: `DecisionAnalyzer` (LLM wrapper).
  - `scoring/` – **Domain Service**: `openskill` wrapper.

**God Files/Folders:**
- **`IntimationRepository` (`storage/repository.py`)**: This class is becoming a "kitchen sink." It handles raw SQL, Ibis expressions, `Intimation` storage, `AnalysisResult` storage, and `LawyerRating` calculations. It mixes concerns (data access vs. aggregation).

## 3. Strengths
- **Clear Composition Root**: The `cli.py` properly instantiates dependencies and passes them into pipeline functions. This makes unit testing the pipelines significantly easier.
- **Modern Stack**: Effective use of `ibis` + `duckdb` allows for powerful local analytics without the overhead of a heavy RDBMS. `pydantic` ensures type safety at boundaries.
- **Async-First**: The architecture is correctly built around `asyncio` to handle the high-latency operations (network requests, LLM calls) inherent to the domain.
- **Pipeline Separation**: Splitting the workflow into distinct phases (`collect`, `archive`, `analyze`, `score`) allows for resuming processing and isolated scaling of specific steps.
- **Developer Experience**: Strong tooling adoption (`uv`, `ruff`, `pre-commit`) and a clear `Makefile`/CLI structure reduce friction for new contributors.

## 4. Key problems & smells (architecture-level)

- **Anemic Domain Model**
  - *Description*: `Intimation` and `Lawyer` are just data holders (Pydantic models). Business logic (e.g., "is this decision ready for analysis?", "who won this case?") is scattered across `pipeline/analyze.py` and `pipeline/score.py`.
  - *Risk*: Logic duplication and tight coupling. If the definition of a "valid win" changes, you have to hunt through pipeline scripts rather than updating a domain entity.

- **Repository "God Class"**
  - *Description*: `IntimationRepository` handles too many distinct aggregates. It manages Intimations, Analysis Results, and Lawyer Ratings.
  - *Risk*: This class will grow indefinitely. It violates the Single Responsibility Principle and makes testing harder because you need a complex mock for any operation.

- **Leaky Repository Abstractions**
  - *Description*: Methods like `get_unanalyzed_intimations` return `list[dict[str, Any]]`.
  - *Risk*: Consumers (pipelines) act on implicit dictionary keys (`item["id"]`) rather than typed objects. This defeats the purpose of Pydantic and leads to runtime `KeyError`s if the schema changes.

- **Implicit Business Logic in Pipelines**
  - *Description*: `run_analysis` manually constructs the result dictionary: `{"outcome": ..., "winner_lawyer": ...}`.
  - *Risk*: This is domain logic (factory/construction) leaking into the orchestration layer. It makes the pipeline hard to read and the construction logic hard to reuse.

## 5. Refactoring roadmap

### Step 1: Fix Repository Return Types
- **Goal**: Ensure repository methods return Domain Entities (`Intimation`), not raw dictionaries.
- **Scope**: `storage/repository.py`, `pipeline/analyze.py`, `pipeline/archive.py`.
- **How**: Modify `get_unanalyzed_intimations` to convert DB rows back into `Intimation` objects before returning. Update the pipeline to access attributes (`item.id`) instead of keys (`item["id"]`).

### Step 2: Extract Lawyer Rating Repository
- **Goal**: Decompose the "God Repository."
- **Scope**: `storage/repository.py` → `storage/repositories/lawyer_repository.py`.
- **How**: Move `get_lawyer_ratings` and `save_lawyer_ratings` into a new `LawyerRatingRepository`. Update `cli.py` to inject this new repository into the `score` pipeline.

### Step 3: Encapsulate Analysis Result Creation
- **Goal**: Remove domain logic from `pipeline/analyze.py`.
- **Scope**: `domain/factories.py` (new) or `domain/models.py`.
- **How**: Create a factory method or domain service (e.g., `AnalysisResult.from_analyzer_output(...)`) that handles the mapping of LLM output to the persistence format, including fallback logic for failures. The pipeline should just call this method.

### Step 4: Isolate Scoring Domain Logic
- **Goal**: Make scoring pure and testable without a DB.
- **Scope**: `pipeline/score.py` → `domain/scoring_service.py`.
- **How**: Move the logic that calculates new ratings (OpenSkill math, updating stats) into a pure domain function `calculate_new_ratings(current_ratings, match_results)`. The pipeline becomes a dumb orchestrator: Fetch data -> Call Service -> Save data.

## 6. Updated target architecture (conceptual)

```
src/causaganha/
  ├── domain/                # PURE PYTHON (No Ibis, No HTTP)
  │   ├── models.py          # Intimation, Lawyer, AnalysisResult
  │   └── services.py        # Scoring logic, validation rules
  ├── application/           # (New) USE CASES
  │   ├── analysis.py        # "AnalyzeDecisionUseCase"
  │   └── scoring.py         # "UpdateRatingsUseCase"
  ├── infrastructure/        # ADAPTERS
  │   ├── persistence/       # Ibis/DuckDB repositories
  │   ├── external/          # PJeAPIClient, GeminiAnalyzer
  │   └── storage/           # DocumentService, ArchiveService
  └── presentation/
      └── cli.py             # Composition Root & Entry Point
```

**Key Benefits:**
- **Decoupling**: The `domain` layer knows nothing about DuckDB or Gemini.
- **Discoverability**: A new developer can look at `domain/services.py` to understand *how* lawyers are rated, without wading through DB fetching code.
- **Testability**: Domain logic can be unit tested with simple Python objects, no mocks required.

## 7. Guardrails & conventions

- **Repository Rule**: Repositories must **always** return Pydantic models (Domain Entities), never `dict` or `ibis.Table`.
- **Pipeline Rule**: Pipelines should only **orchestrate**. They should not contain `if/else` logic about business rules (e.g., "if score < 0"). Delegate that to the Domain.
- **Dependency Rule**: `domain/` modules must not import from `api/`, `storage/`, or `pipeline/`.
- **Schema Separation**: Keep DB schema definitions (`storage/schema.py`) separate from Domain Models (`domain/models.py`). They can evolve independently (e.g., for performance optimizations).
