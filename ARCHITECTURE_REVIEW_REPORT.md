# Architecture Review Report

## 1. High-level Overview

The `causaganha` repository is a data pipeline platform designed to collect judicial intimations, archive documents, analyze legal decisions using LLMs, and calculate lawyer performance ratings. The current architecture is a **Hybrid Monolith**, characterized by a transition state between a legacy "Layered Architecture" (V1) and a newer "Script-based / Vertical Slice" architecture (V2).

**Top-level Components:**
- **`src/causaganha/v2/pipeline/`**: The core orchestration layer. Contains procedural scripts for the four main stages: `collect`, `archive`, `analyze`, and `score`.
- **`src/causaganha/v2/storage/`**: centralized data access layer using DuckDB and Ibis.
- **`src/causaganha/v2/api/`**: Clients for external services (PJe).
- **`src/causaganha/cli.py`**: The application entry point (Composition Root), tying V2 pipelines together with some legacy V1 infrastructure.
- **`src/causaganha/{domain, application, infrastructure}/`**: Legacy V1 components. While "legacy", the domain scoring logic (`openskill`) and document services are still actively used by V2.

## 2. Architecture Map

```text
src/causaganha/
├── cli.py                    # [Entry Point] Orchestrates pipelines
├── v2/
│   ├── pipeline/             # [Orchestration] Procedural scripts ("Services")
│   │   ├── collect.py        # Fetches data, calls API + Storage
│   │   ├── analyze.py        # Calls LLM + Storage
│   │   └── score.py          # Calculates ratings
│   ├── api/                  # [Infra/Adapter] External API Clients (PJe)
│   ├── storage/              # [Infra/Adapter] Database Access
│   │   └── queries.py        # !! [God Module] All SQL queries live here
│   └── analysis/             # [Domain/Infra] LLM Models & Prompts
├── domain/                   # [Shared Kernel] Core logic reused by V1 & V2
│   └── scoring/              # OpenSkill wrapper
├── infrastructure/           # [Legacy Infra]
│   └── clients/              # Document & Archive services (used by CLI)
└── tests/                    # Split into root (V1) and v2/ folders
```

## 3. Strengths

- **Modern Tech Stack**: Effectively uses **DuckDB** for analytical storage, **Pydantic** for robust data validation, and **Typer** for a clean CLI.
- **Clear Pipeline Stages**: The four-step process (Collect → Archive → Analyze → Score) is explicitly defined in the directory structure, making the high-level workflow easy to grasp.
- **Strong Typing**: Pydantic models are used extensively for API responses and LLM outputs, reducing runtime type errors.
- **Separation of Concerns (Conceptual)**: Even if implemented procedurally, there is a clear distinction between "fetching data" (`api`), "saving data" (`storage`), and "running logic" (`pipeline`).
- **Shared Kernel**: The scoring logic (`openskill`) is isolated in `domain/`, showing an intent to keep complex math logic separate from plumbing.

## 4. Key Problems & Smells

- **Hybrid "Split-Brain" Architecture**:
  - *Problem*: V1 (Layered) and V2 (Pipeline) coexist with significant duplication (e.g., `Intimation` model exists in both `domain/models.py` and `v2/api/client.py`).
  - *Risk*: Confusion for new contributors. Logic fixes might be applied to one version and missed in the other.
- **"God Module" Storage**:
  - *Problem*: `src/causaganha/v2/storage/queries.py` contains raw SQL for *all* features (Intimations, Lawyers, Ratings, Analysis).
  - *Risk*: High coupling. Changing the schema requires modifying this one giant file, leading to merge conflicts and accidental breakages of unrelated features.
- **Hard-coded Dependencies (No DI)**:
  - *Problem*: Pipelines like `collect.py` directly instantiate `PJeAPIClient` and call `get_connection()`.
  - *Risk*: Makes unit testing difficult. Tests must mock the network or DB globally rather than injecting a mock adapter. It prevents swapping implementations (e.g., a "Simulation" API client).
- **Anemic Domain in V2**:
  - *Problem*: V2 focuses on "scripts". Business rules (e.g., "What is a valid win?", "When should we archive?") are buried inside `pipeline/*.py` or `storage/queries.py` rather than in clear Domain Entities.
  - *Risk*: Business logic is tightly coupled to infrastructure code, making it hard to extract or reason about independently.
- **Inconsistent Abstractions**:
  - *Problem*: `CLI` uses `DocumentService` (V1 Class) for archiving but calls `collect_metadata_for_all_courts` (V2 Function) for collection.
  - *Risk*: Cognitive load. Developers have to switch mental models between "Service Objects" and "Functional Scripts".

## 5. Refactoring Roadmap

This roadmap focuses on stabilizing the V2 architecture and gradually absorbing useful parts of V1, moving towards a **Modular Service Architecture**.

**Phase 1: Decoupling & Testing (High Impact)**
1.  **Introduce Interfaces for V2 Dependencies**:
    -   *Goal*: Define protocols for `ApiClient`, `StorageRepository`.
    -   *Action*: Create `v2/interfaces.py`. Update pipelines to accept these interfaces as arguments.
2.  **Refactor Pipelines to use Dependency Injection**:
    -   *Goal*: Remove `PJeAPIClient()` instantiation from `collect.py`.
    -   *Action*: Update `collect_metadata_for_all_courts` to accept a `client` instance. Wire it up in `cli.py`.

**Phase 2: Data Access Refactoring**
3.  **Split `queries.py` into Repositories**:
    -   *Goal*: Kill the "God Module".
    -   *Action*: Create `v2/repositories/intimation_repo.py`, `v2/repositories/rating_repo.py`. Move relevant SQL functions there.
4.  **Consolidate Domain Models**:
    -   *Goal*: Single source of truth for `Intimation` and `Lawyer`.
    -   *Action*: Move the richest model (likely V2's or a merge) to `src/causaganha/core/domain`. Delete the duplicates.

**Phase 3: Logic Extraction**
5.  **Extract Service Layer from Pipelines**:
    -   *Goal*: Pipelines should just be "glue". Logic goes to Services.
    -   *Action*: Move scoring calculation loop from `pipeline/score.py` into a `ScoringService` class. The pipeline script effectively becomes a Controller that calls the Service.

## 6. Updated Target Architecture (Conceptual)

The goal is a **Modular Architecture** where "Pipelines" act as Application Services/Use Cases, orchestrating pure Domain Logic and using Infrastructure via Interfaces.

```text
src/causaganha/
├── core/                     # [Inner Layer] No external deps
│   ├── domain/               # Entities (Intimation, Lawyer) & Logic
│   └── interfaces/           # Ports (IntimationRepo, APIClient)
├── infra/                    # [Outer Layer] Implementation details
│   ├── pje/                  # PJe API Client implementation
│   ├── storage/              # DuckDB Repositories
│   └── analysis/             # LLM Client adapters
├── app/                      # [Application Layer] Use Cases
│   ├── collection_service.py # "Collect" logic (formerly pipeline/collect)
│   └── scoring_service.py    # "Score" logic
└── cli.py                    # [Composition Root] Wires Infra to App
```

**Benefits:**
- **Testability**: Services accept Mocks.
- **Clarity**: "Core" contains the business truth. "Infra" contains the messy details.
- **Stability**: Changing the DB only affects `infra/storage`, not the core logic.

## 7. Guardrails & Conventions

Add these to `CONTRIBUTING.md`:

1.  **Dependency Rule**: `core` (Domain) cannot import from `infra` or `app`.
2.  **No "God Files"**: If a file exceeds 400 lines or handles two distinct concepts (e.g., "Saving Intimations" and "Calculating Ratings"), split it.
3.  **Explicit Dependencies**: Functions/Classes should ask for what they need (DI) rather than creating it.
    - *Bad*: `def process(): client = ApiClient() ...`
    - *Good*: `def process(client: ApiClient): ...`
4.  **Pipelines are Orchestrators**: Pipeline scripts should generally *not* contain `if/else` business logic. They should simply pass data from Source A to Service B to Storage C.
