# Architecture Review: CausaGanha

## 1. High-level overview

**CausaGanha** is a judicial analytics platform designed to ingest, analyze, and rate lawyer performance based on Brazilian judicial data. It operates as a **Pipeline-Centric Modular Monolith**, where the primary architectural unit is the "pipeline" (collection, analysis, scoring) rather than domain services. The system relies heavily on **DuckDB** for local analytical storage and **Pydantic AI** for LLM-based classification of judicial decisions.

**Main Top-Level Components:**
*   `src/causaganha/cli/`: The entry point (`Typer` app) that exposes commands like `analyze`, `score`, and `export`.
*   `src/causaganha/pipeline/`: The "thick" orchestration layer containing the bulk of the business logic, loops, and error handling.
*   `src/causaganha/analysis/`: Domain logic for classifying text using LLMs (Gemini) and RAG strategies.
*   `src/causaganha/storage/`: Database interaction layer using `Ibis` and raw SQL, acting as a functional DAO.
*   `src/causaganha/scoring/`: Implementation of the OpenSkill rating algorithm.
*   `src/causaganha/catalog/`: Metadata management for DuckDB/Parquet assets.

## 2. Architecture map

```text
src/causaganha/
├── cli/                 # [Entry Point] Wired to pipelines
│   └── __init__.py      # Composition Root (currently implicit)
│
├── pipeline/            # [Orchestration + Logic] "God Layer"
│   ├── analyze.py       # Orchestrates Analysis Strategy (RAG/LLM/Hybrid)
│   ├── score.py         # Orchestrates Rating calculations
│   └── collect.py       # Orchestrates Data Ingestion
│
├── analysis/            # [Domain: Analysis]
│   ├── models.py        # Core Domain Models (DecisionAnalysis, Outcome)
│   ├── analyzer.py      # LLM implementation (Pydantic AI)
│   └── rag_analyzer.py  # RAG implementation
│
├── scoring/             # [Domain: Rating]
│   └── openskill.py     # Rating algorithm logic
│
├── storage/             # [Infrastructure: Persistence]
│   ├── connection.py    # Singleton DuckDB connection
│   ├── queries.py       # Functional DAO (Mixed Ibis/SQL)
│   └── schema.sql       # Database Schema
│
└── clients/             # [Infrastructure: External Services]
    ├── archive.py       # Internet Archive integration
    └── pje.py           # Legacy Court API client
```

**Highlight:** `src/causaganha/pipeline/analyze.py` is a problematic "hub" that mixes orchestration (batching), infrastructure concerns (cost calculation, logging), and business rules (strategy selection), while directly importing low-level storage functions.

## 3. Strengths

*   **Strong Domain Modeling:** The use of `Pydantic` models in `analysis/models.py` (e.g., `DecisionAnalysis`) provides a clear, type-safe definition of the core domain entities, including robust validators for normalization.
*   **Modern Data Stack:** Leveraging **DuckDB** + **Ibis** allows for efficient local analytics and easy SQL interoperability without the overhead of a heavy RDBMS.
*   **Clear Functional Separation:** The top-level directory structure (`analysis`, `pipeline`, `storage`) makes it easy to locate code by technical concern.
*   **Explicit Entry Points:** The `Typer` CLI clearly defines the available operations and their arguments, serving as good documentation for system capabilities.
*   **Validation-First Approach:** The system extensively validates external data (LLM outputs) at the boundary using Pydantic, preventing "garbage in" from polluting the database.

## 4. Key problems & smells (architecture-level)

*   **Thick Pipelines / Missing Service Layer:**
    *   *Why:* Logic for "how to analyze a batch" or "how to calculate ratings" is trapped in `pipeline/*.py` scripts.
    *   *Risk:* Makes it impossible to reuse this logic (e.g., in an API or a different script) without invoking the entire CLI command flow. It also hinders unit testing.

*   **Storage Implementation Leakage:**
    *   *Why:* `storage/queries.py` functions return raw `dicts` or `pandas.DataFrames` instead of domain objects. Consumers (pipelines) are coupled to the database schema structure.
    *   *Risk:* Renaming a database column requires changes in the storage layer *and* every pipeline that consumes that query.

*   **Implicit Dependencies (No DI):**
    *   *Why:* Pipelines instantiate `DecisionAnalyzer` or `get_connection()` directly.
    *   *Risk:* High coupling makes it difficult to swap implementations (e.g., a mock analyzer) for testing. Tests often rely on heavy patching or "live" integration tests.

*   **Mixed Abstraction Levels in Storage:**
    *   *Why:* `storage/queries.py` mixes high-level Ibis table operations with raw `con.con.execute("INSERT INTO ...")` SQL strings.
    *   *Risk:* Increases the surface area for SQL injection (though parameterized queries are used) and makes the code harder to read/maintain compared to a consistent Ibis or ORM approach.

*   **Global State:**
    *   *Why:* The `get_connection` singleton in `storage/connection.py` is accessed globally.
    *   *Risk:* Makes parallel testing difficult and hides database dependencies from the call graph.

## 5. Refactoring roadmap

**Step 1: Formalize Domain Entities**
*   **Scope:** `src/causaganha/domain/`
*   **Goal:** Ensure `Intimation`, `Lawyer`, and `Rating` are defined as Pydantic models (like `DecisionAnalysis` already is) decoupled from DB schema.
*   **How:** Create `domain/entities.py`. Move `DecisionAnalysis` there. Define `Intimation` model.

**Step 2: Extract Repositories**
*   **Scope:** `src/causaganha/storage/repositories/`
*   **Goal:** Replace `queries.py` with `IntimationRepository` and `AnalysisRepository`.
*   **How:** Create classes that accept a `DuckDB` connection. Methods should accept/return Domain Entities (from Step 1), not dicts. encapsulate all SQL/Ibis logic here.

**Step 3: Extract Application Services**
*   **Scope:** `src/causaganha/services/`
*   **Goal:** Move business logic out of `pipeline/`.
*   **How:** Create `AnalysisService` class. It should take `IntimationRepository` and `DecisionAnalyzer` as dependencies. Move the batching/strategy logic from `pipeline/analyze.py` into this service.

**Step 4: Dependency Injection in CLI**
*   **Scope:** `src/causaganha/cli/__init__.py`
*   **Goal:** Wire up the graph at the entry point.
*   **How:** Instantiate `connection`, `repositories`, `analyzer`, and `service` in the CLI command, then pass the `service` to the (now thin) pipeline function.

**Step 5: Standardize Storage Access**
*   **Scope:** `src/causaganha/storage/`
*   **Goal:** Remove raw SQL where possible.
*   **How:** Refactor repositories to use `Ibis` for inserts/updates if supported, or strictly isolated SQL files/constants.

## 6. Updated target architecture (conceptual)

**Layered Architecture:**

1.  **Presentation (CLI):** `src/causaganha/cli/`
    *   Responsible for parsing arguments, wiring dependencies (Composition Root), and printing output.
    *   *Dependencies:* Services, Domain.

2.  **Application (Services):** `src/causaganha/services/`
    *   Orchestrates domain logic (e.g., `AnalysisService.process_pending()`).
    *   Defines Use Cases.
    *   *Dependencies:* Domain, Repository Interfaces.

3.  **Domain (Core):** `src/causaganha/domain/`
    *   Pure Python objects (Pydantic). Business rules independent of infra.
    *   *Dependencies:* None.

4.  **Infrastructure:**
    *   `src/causaganha/storage/` (Repositories implementation).
    *   `src/causaganha/analysis/` (LLM/AI implementation).
    *   *Dependencies:* Domain.

**Cross-Cutting:**
*   **Configuration:** Passed via dependency injection (Pydantic Settings).
*   **Logging:** `structlog` configured at entry point.

## 7. Guardrails & conventions

*   **No SQL in Pipelines/Services:** All database interaction must go through a Repository method.
*   **No Dicts for Data:** Repositories must return Pydantic models (Domain Entities), not raw dictionaries or DataFrames (unless explicitly for bulk export).
*   **Dependency Injection:** Do not instantiate "heavy" objects (DB connections, API clients) inside logic functions. Accept them as arguments.
*   **Domain Purity:** Domain models should not import from `storage` or `cli`.
*   **Explicit Transactions:** Services should define transaction boundaries (if/when DuckDB supports multi-statement transactions meaningfully), or Repositories should handle atomic operations.
