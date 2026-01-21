# Architecture Review Report

**Date:** December 2024
**Repository:** CausaGanha
**Status:** Hybrid Monolith / Transitional State

---

## 1. High-level Overview

**Purpose:** CausaGanha is a judicial analytics platform designed to collect legal proceedings (intimations) from Brazilian courts (PJe), archive documents, analyze decisions using AI (LLM/RAG), and score lawyer performance using the OpenSkill algorithm.

**Current Architecture:** The repository is currently in a **"Hybrid Monolith"** state. It contains two distinct architectural styles living side-by-side:
1.  **Legacy V1 (Active):** A layered architecture (`application`, `domain`, `infrastructure`) which still provides critical services like Archiving and Shared Domain logic.
2.  **Modern V2 (Target):** A modular, pipeline-centric architecture (`v2/api`, `v2/storage`, `v2/analysis`, `v2/pipeline`) which handles the core workflow (Collect, Analyze, Score).

The application entry point (`cli.py`) acts as a bridge, orchestrating V2 pipelines which in turn occasionally reach back into V1 infrastructure. This creates a functional but structurally inconsistent codebase.

**Top-Level Components:**
-   `src/causaganha/cli.py`: The Composition Root. It orchestrates V2 pipelines.
-   `src/causaganha/v2/`: The core V2 implementation (API, Storage, Analysis, Pipelines).
-   `src/causaganha/infrastructure/`: V1 infrastructure services (Document download, Internet Archive upload) used by V2.
-   `src/causaganha/domain/`: V1 domain models and shared kernels (OpenSkill scoring).
-   `src/causaganha/application/`: V1 application logic (mostly superseded by `v2/pipeline`).

---

## 2. Architecture Map (Textual)

The reality of the codebase diverges significantly from the documentation (`CLAUDE.md`, `AGENTS.md`), which claims V1 is archived.

```text
src/causaganha/
├── cli.py                     # [HYBRID] Entry point. Imports V2 pipelines AND V1 infra services.
├── v2/                        # [TARGET] The intended modern architecture.
│   ├── api/                   # PJe Client (Httpx + Pydantic).
│   ├── storage/               # Ibis + DuckDB data access.
│   ├── analysis/              # AI Analysis (PydanticAI).
│   └── pipeline/              # Orchestration (Collect, Analyze, Archive, Score).
├── infrastructure/            # [LEGACY/SHARED] V1 Infrastructure.
│   ├── clients/               # Used by V2 for Archiving (DocumentService, ArchiveService).
│   └── ...
├── domain/                    # [LEGACY/SHARED] V1 Domain.
│   └── scoring/               # OpenSkill logic used by V2 Score pipeline.
├── application/               # [LEGACY] V1 Pipelines (Superseded but present).
└── ...
```

**God Modules / Hotspots:**
-   `src/causaganha/v2/storage/queries.py`: A "God Module" handling all database queries. It couples storage logic with business entities and is growing indefinitely.
-   `src/causaganha/cli.py`: While acting as a composition root, it explicitly imports from disparate architectural layers (V1 Infra + V2 Pipelines), making it hard to test without complex mocking.

---

## 3. Strengths

-   **Modular V2 Core:** The `src/causaganha/v2` directory demonstrates a clear separation of concerns (API vs Storage vs Analysis).
-   **Modern Tech Stack:** V2 successfully leverages `ibis` for high-performance data manipulation and `pydantic-ai` for structured LLM interactions.
-   **Testability (V2):** V2 components like `collect` and `analyze` are designed with dependency injection in mind (mostly) and are well-covered by tests in `tests/v2`.
-   **Strong Typing:** The pervasive use of Pydantic models in V2 ensures data consistency across boundaries.
-   **Shared Kernel:** The reuse of `domain/scoring` avoids logic duplication for complex algorithms like OpenSkill.

---

## 4. Key Problems & Smells

1.  **Documentation vs. Reality Gap**
    -   *Issue:* `CLAUDE.md` claims V1 is in `legacy_archive/`. It is not. It is mixed in `src/`.
    -   *Risk:* High confusion for new contributors and AI agents. Risk of modifying legacy code thinking it's active, or failing to find active code.

2.  **Broken E2E Tests**
    -   *Issue:* `tests/e2e/test_full_lifecycle.py` mocks symbols (`causaganha.cli.PJeAPIClient`) that are no longer imported by `cli.py`.
    -   *Risk:* The primary end-to-end safety net is likely ineffective or testing a phantom configuration, masking regressions in the CLI wiring.

3.  **Inverted Dependencies**
    -   *Issue:* `v2/pipeline/archive.py` imports `infrastructure` (V1) services. The "new" system depends on the "old" system.
    -   *Risk:* Cannot remove V1 without breaking V2. Creates a "distributed monolith" effect where layers are tangled.

4.  **Logic Duplication**
    -   *Issue:* `PJeAPIClient` exists in both `infrastructure` (V1) and `v2/api` (V2).
    -   *Risk:* Bug fixes in one client might be missed in the other. Maintenance burden is doubled.

5.  **God Module (`queries.py`)**
    -   *Issue:* `v2/storage/queries.py` contains all SQL/Ibis logic.
    -   *Risk:* As the app grows, this file will become unmaintainable. It violates the Single Responsibility Principle.

---

## 5. Refactoring Roadmap

**Priority 1: Sync & Safety**
1.  **Update Documentation**: Rewrite `CLAUDE.md`, `AGENTS.md` to reflect the *actual* Hybrid state. Acknowledge V1 presence in `src/`.
2.  **Fix E2E Tests**: Update `tests/e2e/test_full_lifecycle.py` to correctly patch the V2 pipelines used by `cli.py`, or move it to `tests/v2/e2e` and modernize it.

**Priority 2: Decoupling**
3.  **Port Archive Service to V2**: Re-implement `ArchiveService` and `DocumentService` in `src/causaganha/v2/infrastructure` (or `v2/services`), removing the dependency on V1 `infrastructure`.
4.  **Extract Repositories**: Refactor `v2/storage/queries.py` into specific repository classes (e.g., `IntimationRepository`, `AnalysisRepository`) to break the God Module.

**Priority 3: Structural Migration**
5.  **The "Great Switch"**:
    -   Create `legacy_archive/`.
    -   Move `application`, `domain`, `infrastructure` to `legacy_archive/` (except `domain/scoring` which should move to `v2/domain` or `v2/scoring`).
    -   Promote `v2/*` contents to `src/causaganha/` (flattening the structure).
    -   Update all imports.

---

## 6. Updated Target Architecture (Conceptual)

After the "Great Switch", the repository should look like this:

```text
src/causaganha/
├── cli.py               # Main CLI
├── api/                 # PJe Integration (External System Adapter)
├── storage/             # Database Adapters (Ibis/DuckDB)
├── analysis/            # AI/LLM Logic (Domain Service)
├── pipeline/            # Application Services / Orchestration
├── scoring/             # OpenSkill Logic (Domain Kernel)
└── legacy_archive/      # Truly archived V1 code
```

**Cross-Cutting Concerns:**
-   **Config:** Centralized in `config.py` (already present).
-   **Logging:** Structured logging via `structlog` (already present).
-   **Observability:** Pipelines should emit events/metrics (currently just logs).

---

## 7. Guardrails & Conventions

1.  **V2 First:** All new features MUST go into `src/causaganha/v2/`. No new code in `application`, `domain` (except scoring), or `infrastructure`.
2.  **Layer Isolation:**
    -   `api` and `storage` are siblings; they must NOT import each other.
    -   `pipeline` orchestrates them.
    -   `analysis` should be pure domain logic where possible (or an adapter to LLMs).
3.  **Pipeline Pattern:** Use the "Pipeline" pattern for complex workflows: Fetch Data -> Process -> Store. Do not mix side-effects inside pure processing functions.
4.  **Test Location:** V2 tests must live in `tests/v2/`.
5.  **No God Modules:** If a file exceeds 500 lines or handles multiple distinct entities (e.g., both Users and Documents), split it.
