# Architecture Review Report

**Date:** June 2025
**Repository:** CausaGanha
**Status:** **BROKEN / Partial Migration**

---

## 1. High-level Overview

**Purpose:** CausaGanha is a judicial analytics platform designed to collect legal proceedings from PJe (Electronic Judicial Process), archive them, analyze decisions using AI (LLM/RAG), and score lawyer performance.

**Current Architecture:** The repository is in a **broken state** following an apparent "flattening" migration from a `v2/` subdirectory to the root `src/causaganha/`.
-   **Style:** Intended "Vertical Slice" (Script-based) architecture.
-   **Reality:** Key components are missing (`collect.py`, `api/client.py`), causing the application to crash on startup. The CLI acts as a Composition Root but currently fails due to `ImportError`.

**Top-Level Modules:**
-   `src/causaganha/cli/`: Command-line interface (Typer).
-   `src/causaganha/pipeline/`: Orchestration logic (Analyze, Score, Archive). **CRITICAL:** `collect.py` is missing.
-   `src/causaganha/analysis/`: Domain logic for AI analysis (PydanticAI + RAG).
-   `src/causaganha/storage/`: Data access layer (Ibis + DuckDB).
-   `src/causaganha/api/`: Intended API client module. **CRITICAL:** Currently empty/missing `client.py`.

---

## 2. Architecture Map (Current State)

```text
src/causaganha/
├── cli.py                     # [CRITICAL] Import errors (missing collect)
├── pipeline/                  # Orchestrators
│   ├── analyze.py             # Active: AI Analysis pipeline
│   ├── score.py               # Active: OpenSkill scoring
│   ├── archive.py             # Active: Internet Archive upload
│   └── collect.py             # [MISSING] File does not exist!
├── analysis/                  # Core Domain (AI)
│   ├── models.py              # Pydantic Models (DecisionAnalysis)
│   ├── rag_analyzer.py        # RAG Logic
│   └── vector_store.py        # Embeddings
├── storage/                   # Infrastructure
│   ├── queries.py             # [GOD MODULE] All SQL/Ibis logic
│   ├── schema.sql             # DB Schema
│   └── connection.py          # DB Connection Factory
├── api/                       # Infrastructure
│   └── client.py              # [MISSING] File does not exist!
└── clients/                   # [LEGACY?] V1 Clients (Archive, Document)
```

**God Files/Folders:**
-   `storage/queries.py`: Contains *all* data access logic, mixing domains (Lawyers, Intimations, Analysis). It is the single point of failure for database interactions.

---

## 3. Strengths

-   **Vertical Slices (Intent):** The `pipeline/` directory structure suggests a move towards independent, runnable workflows (Collect, Analyze, Score), which simplifies testing and execution.
-   **Modern Data Stack:** usage of `ibis` and `duckdb` allows for portable, SQL-heavy data transformations without ORM overhead.
-   **Structured AI Output:** `analysis/models.py` uses `pydantic` heavily for robust validation of LLM outputs (cleaning OABs, normalizing states), which is a best practice.
-   **RAG/Hybrid Strategy:** The analysis pipeline implements a sophisticated "Hybrid" strategy (RAG first, LLM fallback), optimizing for cost vs. accuracy.

---

## 4. Key Problems & Smells

1.  **Missing Critical Components (System Failure)**
    -   *Why:* `src/causaganha/pipeline/collect.py` and `src/causaganha/api/client.py` are referenced in code/imports but do not exist on disk.
    -   *Risk:* The application **cannot run**. `uv run causaganha` fails immediately with `ModuleNotFoundError`.

2.  **"God Module" Persistence (`storage/queries.py`)**
    -   *Why:* A single file contains queries for storing intimations, updating ratings, fetching analysis jobs, and archiving.
    -   *Risk:* High coupling. Changing a query for one domain might break another. Merge conflicts are guaranteed as the team grows.

3.  **Inconsistent Dependency Injection**
    -   *Why:* Some pipelines (`archive.py`) receive services (`DocumentService`) as arguments. Others (`analyze.py`) instantiate `DecisionAnalyzer` or call `get_connection()` directly within the function body.
    -   *Risk:* Makes unit testing difficult (requires complex mocking of globals/internals) and hides dependencies.

4.  **Mixed Legacy/New Patterns**
    -   *Why:* `src/causaganha/clients/` (V1 style) exists alongside `src/causaganha/api/` (V2 style). The CLI imports from both.
    -   *Risk:* Confusion about which HTTP client to use. Duplication of logic (e.g., retries, auth).

5.  **Hardcoded "Vertical" Coupling**
    -   *Why:* Pipelines directly import specific storage functions (`store_analysis`, `get_unanalyzed_intimations`).
    -   *Risk:* The Business Logic (Pipeline) is tightly coupled to the Persistence Mechanism (DuckDB/SQL). You cannot easily swap the backend or test the pipeline in isolation without a real DB.

---

## 5. Refactoring Roadmap

**Priority 1: Fix the Build (Critical)**

1.  **Restore Missing Files**
    -   *Scope:* `api/client.py`, `pipeline/collect.py`.
    -   *How:* Recover these files from the previous `v2/` state or recreate them based on interfaces used in `cli.py` and `queries.py`.
    -   *Goal:* Make `uv run causaganha --help` pass.

**Priority 2: Architecture cleanup**

2.  **Split `queries.py` into Repositories**
    -   *Scope:* `storage/queries.py` -> `storage/repositories/{intimation.py, lawyer.py, analysis.py}`.
    -   *How:* Group related functions into modules or classes.
    -   *Goal:* Break the "God Module", improve discoverability.

3.  **Standardize API Client**
    -   *Scope:* `clients/` and `api/`.
    -   *How:* Merge `clients/` functionality into `api/`. Ensure a single HTTP client handles PJe interactions.
    -   *Goal:* Remove legacy V1 artifacts.

4.  **Enforce Dependency Injection in Pipelines**
    -   *Scope:* `pipeline/*.py`.
    -   *How:* Refactor pipeline functions to accept Repositories and Clients as arguments (Protocol-based if possible), rather than importing/instantiating them.
    -   *Goal:* Improve testability and decoupling.

---

## 6. Updated Target Architecture (Conceptual)

```text
src/causaganha/
├── cli.py                     # Composition Root (Wires implementations to Pipelines)
├── domain/                    # (Optional) Pure business logic/models
│   ├── models.py              # Shared Pydantic Models
│   └── ports.py               # Interfaces for Repositories/Clients
├── pipeline/                  # Application Services / Use Cases
│   ├── collect.py             # "Orchestrator" (Does not know about HTTP details)
│   ├── analyze.py
│   └── score.py
├── adapter/                   # (Renamed from storage/api/infra)
│   ├── pje_api.py             # Implementation of PJeClient
│   ├── duckdb_repo.py         # Implementation of Repository Interfaces
│   └── ia_client.py           # Internet Archive Client
└── infrastructure/            # Cross-cutting
    ├── config.py
    └── logging.py
```

---

## 7. Guardrails & Conventions

1.  **Pipelines are Orchestrators Only:** Pipelines should not contain SQL, HTTP request logic, or low-level parsing. They coordinate `Clients` and `Repositories`.
2.  **Explicit Dependencies:** All external dependencies (DB connection, API Clients) must be passed as arguments to the pipeline entry point (Dependency Injection).
3.  **No "God Modules":** Any file exceeding 300 lines should be a candidate for splitting. `utils.py` or `common.py` are forbidden; use specific names (`date_utils.py`).
4.  **Storage Isolation:** SQL statements must strictly live in `storage/` (or `adapter/persistence`). No `con.execute()` allowed in pipelines.
