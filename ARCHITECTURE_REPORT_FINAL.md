# Architecture Review Report

**Date:** June 2025
**Repository:** CausaGanha
**Status:** Alpha / Active Development

---

## 1. High-level Overview

**Purpose:** CausaGanha is a judicial analytics platform that ingests structured legal data, archives it to the Internet Archive, and uses LLMs/RAG to analyze case outcomes and rate lawyer performance.

**Architecture Style:** **Pipeline-Centric Modular Monolith**. The application is organized around vertical data processing pipelines (Collect → Archive → Analyze → Score) rather than a layered web application structure. It leverages a **Modern Data Stack** approach in Python, using **Typer** for the CLI interface, **Pydantic** for domain modeling, **DuckDB** for embedded analytical storage, and **Ibis** for dataframe-like data manipulation.

**Top-Level Components:**
-   `src/causaganha/cli/`: The single entry point for all operations. Currently a monolithic implementation.
-   `src/causaganha/pipeline/`: Orchestration scripts that bind infrastructure and domain logic to execute workflows.
-   `src/causaganha/analysis/`: The core domain logic for decision classification using AI (LLM/RAG).
-   `src/causaganha/storage/`: Infrastructure layer handling database connections and data access (Repositories).
-   `src/causaganha/clients/`: Infrastructure layer for external services (Internet Archive).

---

## 2. Architecture Map

```text
src/causaganha/
├── cli/
│   ├── __init__.py            # [GOD FILE] Defines AND implements all commands (~850 lines)
│   └── commands/              # [EMPTY] Placeholder for refactoring
├── pipeline/                  # [Application Service] Orchestrators
│   ├── analyze.py             # Coordinates Analysis domain + Storage
│   ├── score.py               # Coordinates Scoring domain + Storage
│   └── ...
├── analysis/                  # [Domain] Core Logic
│   ├── analyzer.py            # AI Analysis logic
│   ├── models.py              # [Domain Model] Pydantic entities (DecisionAnalysis)
│   └── ...
├── storage/                   # [Infrastructure] Data Access
│   ├── repositories/          # [Pattern] Repository implementations
│   │   ├── intimation.py      # Intimation persistence (mixes Ibis + Raw SQL)
│   │   └── analysis.py        # Analysis persistence
│   ├── connection.py          # Database connection factory
│   └── schema.sql             # Database DDL
└── clients/                   # [Infrastructure] External Integrations
    └── archive.py             # Internet Archive client
```

**Highlighted Issues:**
-   **CLI Monolith (`cli/__init__.py`):** This file acts as a massive "God File," containing the definition, argument parsing, UI logic (Rich progress bars), and error handling for every single command. It effectively hides the "Interface" layer in one file.
-   **Empty `commands/` folder:** The intent to modularize the CLI exists but hasn't been executed.

---

## 3. Strengths

-   **Adoption of Repository Pattern:** The previous "God Module" `storage/queries.py` has been successfully refactored into domain-specific repositories (`storage/repositories/`). This significantly improves maintainability and separation of concerns.
-   **Strong Domain Modeling:** `analysis/models.py` uses **Pydantic** to strictly define the `DecisionAnalysis` entity and `Outcome` enums. This ensures that data passing through the system is validated and typed, preventing "stringly typed" logic.
-   **Pipeline Clarity:** The `pipeline/` directory explicitly enumerates the capabilities of the system. A new developer can look at this folder and immediately understand what the software *does* (Analyze, Score, Archive, Collect).
-   **Dependency Isolation:** External integrations (like Internet Archive) are isolated in `clients/`, keeping third-party API details away from core logic.
-   **Modern Stack Choices:** The use of DuckDB + Ibis allows for powerful local analytics without the operational overhead of a separate database server, fitting the "Script-based" architecture well.

---

## 4. Key Problems & Smells (Architecture-Level)

1.  **CLI Monolith (`cli/__init__.py`)**
    -   *Why:* A single file manages ~10 different commands. It mixes UI concerns (spinners, printing) with orchestration logic.
    -   *Risk:* High coupling. Adding a new command increases the noise in this file. Merge conflicts are guaranteed if multiple devs work on different commands.

2.  **Documentation Rot**
    -   *Why:* `ARCHITECTURE_REPORT_V2.md` and `CLAUDE.md` reference files that no longer exist (e.g., `storage/queries.py`) or folders that were never created (`api/`).
    -   *Risk:* New contributors will be confused by the mismatch between the map and the territory. It erodes trust in documentation.

3.  **Raw SQL Leaks in Repositories**
    -   *Why:* While Repositories exist, they often bypass the Ibis abstraction to execute raw SQL (e.g., `con.con.execute("INSERT ... ON CONFLICT...")`).
    -   *Risk:* Reduces the portability of the code (locked to DuckDB SQL syntax). Makes testing harder as it requires a real DuckDB instance rather than mocking the Ibis expression tree.

4.  **Implicit Domain in Pipelines**
    -   *Why:* Much of the "glue code" in `pipeline/` (e.g., calculating savings, batching logic) is actually business logic that belongs in the Domain layer, not the Orchestrator.
    -   *Risk:* Logic cannot be reused easily. Pipelines become "fat services" that are hard to test in isolation.

---

## 5. Refactoring Roadmap

**Goal:** Complete the modularization started with the Repository refactor.

1.  **Step 1: Decompose CLI (High Leverage)**
    -   **Scope:** `src/causaganha/cli/`
    -   **Action:** Move each command group from `__init__.py` into dedicated modules in `commands/` (e.g., `commands/analyze.py`, `commands/db.py`). Use `app.add_typer()` in `__init__.py` to aggregate them.
    -   **Why:** Immediately reduces the God File complexity and makes the interface layer navigable.

2.  **Step 2: Clean Up Documentation**
    -   **Scope:** `CLAUDE.md`, `ARCHITECTURE_REPORT_V2.md`
    -   **Action:** Remove references to `queries.py` and `api/`. Update the architecture diagrams to reflect the current reality (Repositories).
    -   **Why:** prevents confusion and "broken windows" effect.

3.  **Step 3: Standardize Ibis Usage (Long Term)**
    -   **Scope:** `src/causaganha/storage/repositories/`
    -   **Action:** Where possible, replace raw SQL strings with Ibis expressions. For complex `ON CONFLICT` clauses, encapsulate the raw SQL clearly or use Ibis's emerging support for DML if available.
    -   **Why:** Improves type safety and potential backend portability.

---

## 6. Updated Target Architecture (Conceptual)

```text
src/causaganha/
├── cli/                         # [Interface Layer]
│   ├── __init__.py              # Entry point (registers sub-apps)
│   └── commands/                # Command implementations
│       ├── analyze.py           # UI logic for analysis
│       ├── export.py            # UI logic for exports
│       └── ...
├── pipeline/                    # [Application Layer] Use Cases
│   ├── analyze.py               # "AnalyzeDecisions" Use Case
│   └── ...
├── domain/                      # [Domain Layer] Pure Logic
│   ├── analysis/                # Analysis Entities & Services
│   └── scoring/                 # Scoring Algorithms
├── infrastructure/              # [Infrastructure Layer] Adapters
│   ├── storage/                 # Database Adapters
│   │   └── repositories/        # Data Access implementation
│   └── clients/                 # External Service Adapters
```

**Key concept:** The `cli` layer handles *User Interface* (spinners, colors). It calls `pipeline` (Application Services) which orchestrates `domain` logic and persists via `infrastructure`.

---

## 7. Guardrails & Conventions

1.  **CLI is for UI Only:** CLI commands must not contain business logic. They should parse args, start a spinner, call a Pipeline function, and print the result.
2.  **Pipelines are Orchestrators:** Pipelines should not contain complex algorithmic logic. They should delegate to Domain services/models.
3.  **No SQL Outside Repositories:** All database interaction (SQL or Ibis) must be contained within `src/causaganha/storage/repositories/`. No other layer should import `duckdb` or `ibis` directly for data access.
4.  **Test Co-location:** Tests should mirror the source structure. If you add `cli/commands/analyze.py`, add `tests/unit/cli/commands/test_analyze.py`.
