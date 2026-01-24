# Architecture Review Report

**Date:** June 2025
**Repository:** CausaGanha
**Status:** Alpha / Active Development

---

## 1. High-level Overview

**Purpose:** CausaGanha is a judicial analytics platform designed to analyze structured legal data (from DJEN) and rate lawyer performance. Ideally, it acts as a "backend for data processing," consuming Parquet files produced by a separate ingestion system (`djen-scraper`) and producing analyzed outcomes and ratings.

**Architecture Style:** **Pipeline-Centric Modular Monolith**. The application is structured around data processing pipelines (Collect -> Analyze -> Score -> Export) rather than a traditional layered web application. It uses a modern stack ("Modern Data Stack" in Python) leveraging **Ibis** and **DuckDB** for efficient data manipulation, **Typer** for the CLI interface, and **Pydantic** for robust data validation.

**Top-Level Components:**
-   `src/causaganha/cli/`: The application entry point and command definition.
-   `src/causaganha/pipeline/`: Orchestrators that tie together storage, analysis, and clients to execute workflows.
-   `src/causaganha/analysis/`: Core business logic for determining case outcomes (using LLMs/RAG).
-   `src/causaganha/scoring/`: Implementation of the OpenSkill rating algorithm.
-   `src/causaganha/storage/`: Data access layer (DuckDB connection and queries).
-   `src/causaganha/clients/`: Integrations with external services (Internet Archive).
-   `src/causaganha/catalog/`: Management of DuckDB metadata catalogs.

---

## 2. Architecture Map

```text
src/causaganha/
├── cli/                       # [Interface] Command Line Interface
│   ├── __init__.py            # [GOD FILE] Defines ALL commands and app entry point
│   └── commands/              # [EMPTY] Intended for split commands but unused
├── pipeline/                  # [Application] Workflows / Orchestrators
│   ├── analyze.py             # Orchestrates analysis (fetch -> analyze -> store)
│   ├── score.py               # Orchestrates scoring
│   ├── archive.py             # Orchestrates IA upload
│   └── export_*.py            # Orchestrates Parquet exports
├── analysis/                  # [Domain/Service] Core Analysis Logic
│   ├── analyzer.py            # LLM interaction
│   ├── rag_analyzer.py        # RAG logic
│   └── models.py              # Pydantic models for analysis domain
├── scoring/                   # [Domain] Scoring Logic
│   └── openskill.py           # Rating algorithm implementation
├── storage/                   # [Infrastructure] Data Access
│   ├── connection.py          # DuckDB singleton
│   ├── queries.py             # [GOD MODULE] All data access + some logic + raw SQL
│   └── schema.sql             # Database definition
├── clients/                   # [Infrastructure] External Clients
│   └── archive.py             # Internet Archive client
└── catalog/                   # [Domain/Service] Metadata Catalog
    └── creator.py             # Logic to create analytical views
```

**Highlighted Issues:**
-   `src/causaganha/cli/__init__.py`: **God File**. It contains the definition and implementation of *every* CLI command (`collect`, `analyze`, `score`, `db`, `export`, `groundtruth`, `parquet`, `catalog`). It imports from everywhere, making it a massive dependency hub.
-   `src/causaganha/storage/queries.py`: **God Module**. It handles all database interactions for all domains (intimations, lawyers, ratings, analysis) and mixes raw SQL with Ibis logic.

---

## 3. Strengths

-   **Modern Data Stack:** The decision to use **Ibis** + **DuckDB** allows for efficient, SQL-like data manipulation in Python without the overhead of a full ORM for analytics workloads.
-   **Separation of Concerns (Ingestion vs. Processing):** Offloading the complex/brittle scraping logic to `djen-scraper` (Cloudflare Worker) and keeping `causaganha` focused on processing structured data is a strong architectural choice for scalability and maintainability.
-   **Type Safety:** Widespread use of **Pydantic** (in `analysis/models.py`, `api/models.py`) ensures that data moving through the system is validated, reducing runtime errors.
-   **Pipeline Abstraction:** The `pipeline/` directory clearly enumerates the high-level capabilities of the system (Analyze, Score, Export), making it easy to understand "what the system does."
-   **Environment Isolation:** Configuration is centralized in `config.py` using `pydantic-settings` (inferred), promoting 12-factor app principles.

---

## 4. Key Problems & Smells (Architecture-Level)

1.  **Documentation vs. Reality Mismatch**
    -   *Why:* `CLAUDE.md` references an `api/` folder for "DJEN API integration" that does not exist (it's likely `clients/` or externalized). `ARCHITECTURE_REVIEW.md` describes a "hybrid state" with `legacy_archive` that doesn't exist.
    -   *Risk:* High confusion for new contributors (and agents). False mental models lead to bugs and incorrect refactors.

2.  **CLI Monolith (`cli/__init__.py`)**
    -   *Why:* A single file contains ~600 lines of command definitions, mixing UI logic (Typer/Rich) with business orchestration.
    -   *Risk:* High churn in one file. Hard to read. Imports *everything*, causing slow startup times and tight coupling.

3.  **Data Access God Module (`storage/queries.py`)**
    -   *Why:* A single file contains all SQL queries. It mixes domains (Lawyers, Decisions, System Metadata). It also embeds business logic (e.g., deciding which model strings to store based on analysis method).
    -   *Risk:* Violation of Single Responsibility Principle. Merge conflicts are likely. Hard to refactor individual domains (e.g., splitting "Scoring" to a separate service).

4.  **Leaky Abstractions in Storage**
    -   *Why:* `queries.py` relies heavily on `con.con.execute(raw_sql)`. While Ibis is present, the code bypasses it for `ON CONFLICT` and other DML operations, creating a dependency on DuckDB-specific SQL syntax scattered in Python strings.
    -   *Risk:* Hard to test (requires real DB). Vendor lock-in (harder to swap backend if needed, though unlikely for this stack). SQL injection risk (mitigated by params, but still raw SQL).

5.  **Ambiguous "API" vs "Clients"**
    -   *Why:* The codebase uses `clients/` for Internet Archive, but docs talk about `api/`. There is no clear standard for external integrations.
    -   *Risk:* Inconsistent directory structure. "Where do I put the client for Service X?" becomes a guess.

---

## 5. Refactoring Roadmap

**Goal:** Stabilize the structure, clean up "God Files," and align documentation.

1.  **Step 1: Documentation Truth (Immediate)**
    -   **Scope:** `CLAUDE.md`, `ARCHITECTURE_REVIEW.md` (delete).
    -   **Goals:** Remove references to non-existent `api/` and `legacy_archive/`. Document the actual `clients/` and `cli/` structure.
    -   **Plan:** Delete `ARCHITECTURE_REVIEW.md`. Update `CLAUDE.md` to reflect the `src/causaganha/` structure accurately.

2.  **Step 2: Decompose CLI**
    -   **Scope:** `src/causaganha/cli/`.
    -   **Goals:** Move commands from `__init__.py` to `commands/*.py` (e.g., `commands/analyze.py`, `commands/export.py`).
    -   **Plan:** Create submodules in `commands/`. Move `@app.command` functions there. Register them in `__init__.py` or use `app.add_typer`.

3.  **Step 3: Split Storage Queries (Repository Pattern)**
    -   **Scope:** `src/causaganha/storage/`.
    -   **Goals:** Break `queries.py` into domain-specific repositories: `storage/repositories/intimation.py`, `storage/repositories/rating.py`.
    -   **Plan:** Create `storage/repositories/`. Move `store_intimations` to `intimation.py`, `update_lawyer_rating` to `rating.py`. Update imports in pipelines.

4.  **Step 4: Standardize External Integrations**
    -   **Scope:** `src/causaganha/clients/` vs `api/`.
    -   **Goals:** Decide on one name. `clients/` is fine.
    -   **Plan:** If `api/` logic was intended for PJe/DJEN, verify if it's needed. If not, stick to `clients/` and update all docs to refer to `clients/`.

---

## 6. Updated Target Architecture (Conceptual)

```text
src/causaganha/
├── cli/                         # Interface Layer
│   ├── __init__.py              # App entry point (minimal)
│   └── commands/                # Individual command groups
│       ├── analyze.py
│       ├── export.py
│       └── ...
├── pipeline/                    # Application/Orchestration Layer
│   ├── analyze.py
│   └── ...
├── domain/ (Logical)            # Business Logic Layer (scattered currently)
│   ├── analysis/                # Analysis Domain
│   └── scoring/                 # Scoring Domain
├── infrastructure/ (Logical)    # Infrastructure Layer
│   ├── storage/                 # Data Access
│   │   ├── connection.py
│   │   └── repositories/        # [NEW] Domain-scoped repositories
│   │       ├── intimation.py
│   │       └── rating.py
│   └── clients/                 # External Services
│       └── archive.py
```

**Dependency Rules:**
1.  `cli` depends on `pipeline`.
2.  `pipeline` depends on `domain` (Analysis/Scoring) and `infrastructure` (Storage/Clients).
3.  `domain` is pure Python (Pydantic models, algorithms) and **should not** depend on `infrastructure` or `cli`.
4.  `infrastructure` depends on `domain` (for data models) but **not** `pipeline` or `cli`.

---

## 7. Guardrails & Conventions

1.  **No Logic in CLI:** CLI commands should only parse arguments, setup logging/UI, and call a Pipeline function. No DB queries or business logic in `cli/`.
2.  **No Raw SQL in Pipelines:** Pipelines must not call `con.execute()`. They must use functions from `storage/repositories/`.
3.  **Explicit IO Boundaries:** All I/O (Database, Network) must happen in `storage/` or `clients/`. `analysis/` and `scoring/` should be side-effect free (accept data, return data).
4.  **Test Co-location:** Tests should mirror the source structure. `tests/unit/storage` for storage tests, `tests/unit/pipeline` for pipeline tests.
