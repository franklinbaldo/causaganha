# Architecture Review Report

**Date:** December 2024
**Repository:** CausaGanha
**Status:** Alpha / Hybrid Migration State

---

## 1. High-level Overview

**Purpose:** CausaGanha is a judicial analytics platform that collects lawyer performance data from Brazilian courts (PJe), analyzes case outcomes using LLMs (Gemini), and rates lawyers using the OpenSkill algorithm.

**Current Architecture:** The repository is in a **hybrid transitional state** ("Accidental Monolith"). It contains two distinct architectures living side-by-side:
1.  **V1 (Legacy/Current Production):** A layered architecture (`application`, `domain`, `infrastructure`) powered by Pandas and synchronous/async hybrid code. This is what the main CLI currently runs.
2.  **V2 (Under Construction):** A modular, component-based architecture (`api`, `storage`, `analysis`, `pipeline`) powered by Ibis, PydanticAI, and httpx, located in `src/causaganha/v2/`.

**Top-Level Components:**
-   `src/causaganha/cli.py`: The application entry point (currently wired to V1).
-   `src/causaganha/application/`: V1 Use Cases / Pipelines.
-   `src/causaganha/domain/`: V1 Entities and Interfaces.
-   `src/causaganha/infrastructure/`: V1 Adapters (PJe Client, Repositories).
-   `src/causaganha/v2/`: The V2 implementation (API, Storage, Analysis, Pipeline).

---

## 2. Architecture Map

The repository structure does **not** match the documentation (`CLAUDE.md`, `AGENTS.md`), which claims V1 is archived. The reality is:

```text
src/causaganha/
├── cli.py                     # [HYBRID] Entry point (wired mostly to V1)
├── config.py                  # [SHARED] Configuration
├── application/               # [V1] Application Layer
│   └── pipeline/              # V1 logic (analyze, archive, collect, score)
├── domain/                    # [V1] Domain Layer
│   ├── models.py              # V1 Entities
│   └── interfaces.py          # V1 Ports/Protocols
├── infrastructure/            # [V1] Infrastructure Layer
│   ├── integrations/pje/      # V1 PJe Client (Requests/Httpx)
│   └── storage/               # V1 Repositories
├── v2/                        # [V2] The New Architecture
│   ├── api/                   # V2 PJe Client (Httpx + Pydantic Models)
│   ├── storage/               # V2 Ibis + DuckDB Adapters
│   ├── analysis/              # V2 PydanticAI Analyzer
│   └── pipeline/              # V2 Orchestration (collect, analyze, score)
└── ml/                        # [SHARED?] Machine Learning / Embeddings
```

**"God Files" / problematic areas:**
-   `cli.py`: Acts as a confused composition root, mixing imports from V1 (`application`) and potentially V2 in the future.
-   `infrastructure/integrations/pje/client.py` vs `v2/api/client.py`: Almost identical purpose, implemented twice.

---

## 3. Strengths

-   **Clear V2 Vision:** The `v2/` directory has a clean, modular structure that separates concerns effectively (API vs Storage vs Analysis).
-   **Modern Stack (V2):** V2 adopts `pydantic-ai` for structured LLM outputs and `ibis` for performant data operations, addressing V1's bottlenecks.
-   **Type Safety:** Heavy use of Pydantic models in V2 ensures better data validation and type safety compared to V1's dictionaries/Pandas DataFrames.
-   **Layered V1:** The legacy V1 code, while dated, follows a reasonable layered architecture, making it easier to understand even if it's being replaced.
-   **TDD Focus:** There is evidence of strong testing practices, especially for the new V2 components.

---

## 4. Key Problems & Smells

1.  **Documentation vs. Reality Gap (Critical)**
    -   *Why:* `CLAUDE.md` and `AGENTS.md` claim V1 is in `legacy_archive/` and V2 is at the root. This is false.
    -   *Risk:* Agents and new contributors will be confused, potentially modifying V1 thinking it's V2, or failing to find files.

2.  **Logic Duplication**
    -   *Why:* `PJeAPIClient` exists in both `infrastructure` (V1) and `v2/api` (V2). `collect` pipeline exists in both.
    -   *Risk:* Bug fixes applied to one might be missed in the other. Wasted effort maintaining two versions.

3.  **CLI Coupling to Legacy**
    -   *Why:* The main `cli.py` still imports from `application/` (V1). You cannot run V2 pipelines easily from the main entry point.
    -   *Risk:* V2 code is "dead" until it's wired up. It's harder to test V2 in a production-like manner.

4.  **Incomplete V2 Feature Set**
    -   *Why:* V2 has `collect`, `analyze`, `score`, but is missing `archive` (publishing to Internet Archive), which exists in V1.
    -   *Risk:* V2 cannot fully replace V1 yet.

5.  **Ambiguous Shared Ownership**
    -   *Why:* Modules like `ml/` and `schemas/` sit at the root. It's unclear if they are V1 legacies or intended for V2 reuse.
    -   *Risk:* Spaghetti dependencies where V2 might accidentally depend on legacy V1 constructs via these shared modules.

---

## 5. Refactoring Roadmap

**Goal:** Complete the migration to V2 and match the documentation.

1.  **Step 1: Sync Documentation with Reality (Immediate)**
    -   **Scope:** `CLAUDE.md`, `AGENTS.md`, `README.md`.
    -   **Action:** Update docs to acknowledge the current hybrid state. Do NOT pretend `legacy_archive` exists yet.
    -   **Goal:** Prevent agent/developer confusion.

2.  **Step 2: Wire V2 to CLI**
    -   **Scope:** `src/causaganha/cli.py`.
    -   **Action:** Create a `v2` command group (e.g., `causaganha v2 collect`) OR toggle logic to use `v2.pipeline` modules.
    -   **Goal:** Make V2 runnable and testable via the standard interface.

3.  **Step 3: Port "Archive" Pipeline to V2**
    -   **Scope:** `src/causaganha/v2/pipeline/archive.py`.
    -   **Action:** Port the Internet Archive publishing logic from V1 to V2, using V2 storage adapters.
    -   **Goal:** Feature parity.

4.  **Step 4: The "Great Switch" (Structural Migration)**
    -   **Scope:** Entire `src/causaganha/` tree.
    -   **Action:**
        1.  Create `src/causaganha/legacy_archive/`.
        2.  Move `application`, `domain`, `infrastructure` into `legacy_archive/`.
        3.  Move `v2/*` content UP to `src/causaganha/` (flattening V2).
        4.  Fix imports in `cli.py` and `tests/`.
    -   **Goal:** Achieve the target architecture described in `CLAUDE.md`.

5.  **Step 5: Clean up Shared Modules**
    -   **Scope:** `ml/`, `schemas/`.
    -   **Action:** Decide ownership. If `ml` is used by V2, refactor it to use V2 data structures. If `schemas` are redundant with V2 models, delete them.

---

## 6. Updated Target Architecture (Conceptual)

After completing Step 4, the repo will look like this (matching the original plan):

```text
src/causaganha/
├── cli.py               # Main CLI
├── api/                 # PJe Integration (formerly v2/api)
├── storage/             # Ibis/DuckDB (formerly v2/storage)
├── analysis/            # AI Analysis (formerly v2/analysis)
├── pipeline/            # Orchestration (formerly v2/pipeline)
├── scoring/             # OpenSkill Shared Kernel
└── legacy_archive/      # Old V1 code (reference only)
```

**Dependency Rules:**
-   `pipeline` -> `api`, `storage`, `analysis`, `scoring`
-   `api`, `storage`, `analysis` -> **No dependencies on each other** (independent adapters).
-   `legacy_archive` -> **Forbidden** to import from `legacy_archive` in main code.

---

## 7. Guardrails & Conventions

1.  **No New V1 Code:** Do not add features to `application/` or `domain/`. All new features go to `v2/` (or root after migration).
2.  **Strict Layering in V2:**
    -   `storage` should not import `api`.
    -   `api` should not import `storage`.
    -   Pipelines are the only place where these meet.
3.  **IO Isolation:** All IO (Database, HTTP, File System) must happen in `infrastructure` (V1) or `storage`/`api` (V2). Domain logic (scoring, analysis models) must be pure.
4.  **Test Co-location:** Tests for `v2` components must live in `tests/v2` (until the merge, then `tests/`).
5.  **Documentation First:** Update `ARCHITECTURE.md` or `plans/` before starting major refactors.
