# Architecture Review Report

**Date:** June 2025
**Repository:** CausaGanha
**Status:** Hybrid Monolith (Active Migration to V2)

---

## 1. High-level Overview

**Purpose:** CausaGanha is a judicial analytics platform designed to collect legal proceeding data (intimations) from Brazilian courts (PJe), analyze decision outcomes using AI (LLM/RAG), and score lawyer performance using the OpenSkill algorithm.

**Current Architecture:** The system is in a **Hybrid Monolith** state. It is actively migrating from a legacy layered architecture (V1) to a new, script-based pipeline architecture (V2).
-   **V1 (Legacy):** Follows a traditional layered structure (`application`, `domain`, `infrastructure`). It provides shared infrastructure services (like document downloading and archiving) that are still used by V2.
-   **V2 (Active):** A "Vertical Slice" or script-based architecture organized by technical function (`api`, `storage`, `analysis`, `pipeline`). It uses modern libraries (`ibis`, `pydantic-ai`, `httpx`) and is the primary focus of development.

**Top-Level Components:**
-   `src/causaganha/cli.py`: The **Composition Root**. It is primarily wired to V2 pipelines but injects V1 infrastructure services where V2 equivalents are missing.
-   `src/causaganha/v2/`: The core of the new system (API client, Ibis queries, Analysis logic, Orchestration pipelines).
-   `src/causaganha/infrastructure/`: V1 infrastructure layer, currently acting as a "Shared Kernel" for document handling and PJe integrations.
-   `src/causaganha/domain/`: V1 domain logic, largely bypassed by V2 pipelines which contain their own logic.

---

## 2. Architecture Map

```text
src/causaganha/
├── cli.py                     # [HYBRID] Composition Root. Wires V2 pipelines with V1 services.
├── v2/                        # [V2] New Architecture
│   ├── api/                   # PJe API Client (httpx, Pydantic)
│   ├── analysis/              # AI Analysis (PydanticAI, RAG)
│   ├── pipeline/              # Orchestration Scripts (Collect, Analyze, Score, Archive)
│   └── storage/               # Ibis/DuckDB Data Access
├── infrastructure/            # [V1/SHARED] Infrastructure Services
│   ├── clients/               # Document & Archive Services (used by V2)
│   └── integrations/          # Legacy PJe integration
├── domain/                    # [V1] Legacy Domain Models (mostly unused by V2)
└── application/               # [V1] Legacy Application Services (mostly unused by CLI)
```

**"God Modules" & Problem Areas:**
-   `src/causaganha/v2/storage/queries.py`: A massive violation of the Single Responsibility Principle. It mixes SQL queries, business logic (win rates, rating formulas), and serialization for multiple unrelated entities.
-   `src/causaganha/cli.py`: While necessary as a glue layer, it tightly couples the application to specific V2 pipeline implementations and V1 services.

---

## 3. Strengths

-   **Modern Tech Stack (V2):** The adoption of `ibis` for data processing and `pydantic-ai` for structured LLM interactions is a significant improvement over V1's likely Pandas/raw-LLM approach, offering better performance and type safety.
-   **Clear V2 Separation of Concerns (High Level):** The top-level folders in V2 (`api`, `analysis`, `storage`, `pipeline`) clearly denote technical responsibilities.
-   **Strong Verification:** The codebase includes comprehensive tests (`tests/v2/`) and end-to-end verification scripts, ensuring the new architecture works as intended.
-   **Pragmatic Reuse:** V2 correctly reuses V1's robust `infrastructure` components (like `DocumentService` and `ArchiveService`) via dependency injection in pipelines like `archive.py`, rather than rewriting them prematurely.
-   **Type Safety:** Extensive use of Pydantic models in V2 (`v2/api/client.py`, `v2/analysis/models.py`) ensures data consistency across boundaries.

---

## 4. Key Problems & Smells

1.  **"God Module" in Storage (`queries.py`)**
    -   *Why:* `queries.py` contains SQL for every table, logic for ratings (`mu - 3*sigma`), and JSON handling.
    -   *Risk:* Any change to data storage affects all domains. High merge conflict risk. Hard to test logic in isolation from the database.

2.  **Documentation vs. Reality Gap**
    -   *Why:* Documentation claims V1 is in `legacy_archive/`, but it sits in `src/causaganha/{application,domain,infrastructure}`.
    -   *Risk:* Confusion for new contributors/agents. Risk of modifying legacy code thinking it's the "new way" or active code.

3.  **Domain Anemia in V2**
    -   *Why:* V2 lacks a dedicated domain layer. Business logic (scoring, win/loss determination) is scattered between `pipeline/*.py` scripts and `storage/queries.py`.
    -   *Risk:* Business rules are duplicated or hidden in infrastructure code. Hard to reason about core logic without understanding the entire pipeline.

4.  **Implicit V2 dependency on V1**
    -   *Why:* V2 pipelines depend on `infrastructure` (V1) without a clear interface or contract.
    -   *Risk:* Refactoring V1 `infrastructure` might break V2 pipelines silently if not careful.

5.  **Tight Coupling in Pipelines**
    -   *Why:* Pipelines like `analyze.py` and `collect.py` directly instantiate `get_connection()` or `PJeAPIClient`, making them hard to unit test without mocking "the world" (or using the `queries.py` static functions).

6.  **Broken CI & Unrealistic Linting**
    -   *Why:* The `ruff.toml` configuration enables `ALL` rules with `ignore = []`, resulting in over 4,000 linting errors and a permanently broken CI build.
    -   *Risk:* Developers ignore CI signals; code quality actually degrades because "everything fails anyway". Prevents merging valid changes.

---

## 5. Refactoring Roadmap

**Goal:** Clean up the Hybrid state, isolate V1, and fix V2 design flaws.

1.  **Step 1: Formalize "Shared Kernel" (Incremental)**
    -   **Scope:** `src/causaganha/infrastructure/`
    -   **Action:** Explicitly identify which `infrastructure` components are used by V2 (Document, Archive). Move them to `src/causaganha/v2/infrastructure` OR create a root `src/causaganha/shared` module.
    -   **Goal:** Clarify what is "Legacy V1" (to be deleted) vs "Shared Infra" (to be kept).

2.  **Step 2: Isolate Legacy V1**
    -   **Scope:** `application`, `domain`, `infrastructure` (unused parts).
    -   **Action:** Move truly unused V1 code to `legacy_archive/` as the documentation claims.
    -   **Goal:** Match reality to documentation and reduce cognitive load.

3.  **Step 3: Deconstruct `queries.py`**
    -   **Scope:** `src/causaganha/v2/storage/queries.py`
    -   **Action:** Split into domain-specific repositories: `IntimationRepository`, `AnalysisRepository`, `RatingRepository`. Move business logic (scoring formulas) OUT of storage and into `v2/domain` or `v2/analysis`.
    -   **Goal:** Eliminate God Module, improve testability.

4.  **Step 4: Introduce Dependency Injection in Pipelines**
    -   **Scope:** `v2/pipeline/`
    -   **Action:** Refactor `collect.py` and `analyze.py` to accept `PJeAPIClient` and repositories as arguments (like `archive.py` already does).
    -   **Goal:** Make pipelines unit-testable without patching global modules.

---

## 6. Updated Target Architecture (Conceptual)

```text
src/causaganha/
├── cli.py
├── legacy_archive/      # [Deactivated] Old V1 code
├── shared/              # Common Infra (Document, Archive, Logging)
└── v2/
    ├── api/             # External API Clients
    ├── domain/          # [NEW] Pure Business Logic (Rating math, Analysis rules)
    ├── storage/         # Repositories (Ibis/DuckDB)
    │   ├── intimation_repo.py
    │   ├── analysis_repo.py
    │   └── rating_repo.py
    └── pipeline/        # Orchestration (Wires Domain + Storage + API)
```

**Key Changes:**
-   **Repositories:** `storage` implements interfaces defined in `domain` (or just provides clean data access objects).
-   **Pure Domain:** Logic like `mu - 3*sigma` moves to `v2/domain/scoring.py`.
-   **Shared Infra:** Reusable components like PDF downloading live in `shared/` or `v2/infrastructure/`.

---

## 7. Guardrails & Conventions

1.  **V2-Only for New Features:** All new feature development must happen in `src/causaganha/v2`. Do not touch V1 `application/` or `domain/`.
2.  **No Logic in Storage:** `queries.py` (and future repositories) must only handle data access. No math, no status decisions, no "business" defaults.
3.  **Pipeline = Orchestrator:** Pipelines should only *wire* things together. They should not contain complex loops or business rules (delegate to Domain services).
4.  **Explicit Dependencies:** Functions in `pipeline/` must declare their dependencies as arguments (Dependency Injection), avoiding `get_connection()` calls deep in the logic.
