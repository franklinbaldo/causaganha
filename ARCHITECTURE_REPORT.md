# Architecture Review Report: CausaGanha

## 1. High-level Overview

**Purpose:** CausaGanha is a judicial analytics platform that collects Brazilian court decisions (initially TJRO), analyzes them using AI (LLMs) to determine outcomes, and rates lawyers using the OpenSkill algorithm (similar to Elo).

**Current Architecture:** The repository is currently in a **Hybrid / Transition State**.
*   **V1 (Legacy):** A layered architecture (Domain, Application, Infrastructure) that powers the current CLI and Cloud Functions. It relies on scraping (or early API clients), pandas for data manipulation, and direct Google Gemini SDK usage.
*   **V2 (Emerging):** A component-based, vertical-slice architecture (`api`, `storage`, `analysis`, `pipeline`) designed for high performance and scalability. It introduces `pydantic-ai` for structured LLM interactions and `ibis` for efficient data processing, targeting the PJe API directly.

**Top-level Components:**
*   `src/causaganha/domain/`: (V1) Core business entities (Models) and interfaces. Contains the shared `scoring` logic.
*   `src/causaganha/application/`: (V1) Use cases and pipelines (Collect, Analyze, Score).
*   `src/causaganha/infrastructure/`: (V1) Implementations for storage, cloud functions, and API clients.
*   `src/causaganha/v2/`: (V2) The new root for the rewritten system, containing `api`, `storage`, `analysis`, and `pipeline` modules.
*   `src/causaganha/ml/`: (V1) Standalone machine learning components (Online Learner, Embeddings).

## 2. Architecture Map

```text
src/
  causaganha/
    domain/          -- [V1/Shared] Core entities and logic (e.g., scoring/openskill.py)
    application/     -- [V1] Pipeline orchestration (collect, analyze, score)
    infrastructure/  -- [V1] External adapters
       cloud/        -- Cloud Function entry points
       integrations/ -- PJe API Client (V1 implementation)
       storage/      -- DuckDB repositories
    ml/              -- [V1] Machine Learning subsystem (isolated)

    v2/              -- [V2] The Future System
       api/          -- PJe API Client (New implementation using Pydantic V2)
       storage/      -- Data access (Ibis + DuckDB)
       analysis/     -- AI Logic (Pydantic AI + Gemini)
       pipeline/     -- New orchestration workflows
```

**"God Folders" / Anomalies:**
*   `src/causaganha/infrastructure/cloud/`: Replicates some pipeline logic found in `application/`, blurring the boundary between "running the app" and "deploying the app".
*   `src/causaganha/infrastructure/integrations/pje/client.py`: A fully featured V1 API client that overlaps with the intended V2 client.

## 3. Strengths

*   **Clear V2 Vision:** The `causaganha-v2-plan-from-scratch.md` is an exceptionally detailed and well-reasoned architectural document. It correctly identifies V1 pain points (Pandas performance, brittle scraping) and proposes solid solutions (Ibis, Official API).
*   **Domain Isolation:** V1 successfully isolates the core scoring logic (`openskill.py`) in the domain layer, making it reusable for V2 without heavy refactoring.
*   **Modern Stack Choices (V2):** Adopting `pydantic-ai` for structured outputs and `ibis` for backend-agnostic data processing positions the project well for future scale.
*   **TDD Culture:** The V2 plan mandates a strict Test-Driven Development approach, which is critical for a complex data pipeline.

## 4. Key Problems & Smells

*   **Ambiguous "Shared Kernel":**
    *   *Why:* The V2 plan states OpenSkill logic is "unchanged," but it currently lives in `src/causaganha/domain/scoring`. If V2 imports from `domain`, it implicitly couples itself to the V1 structure.
    *   *Risk:* Future refactoring of V1 `domain` could accidentally break V2. V2 should ideally be self-contained or depend on a clearly defined "shared" library.

*   **Duplicated PJe Client Logic:**
    *   *Why:* `src/causaganha/infrastructure/integrations/pje/client.py` (V1) already implements a robust async PJe client. The V2 plan calls for building a new one from scratch.
    *   *Risk:* Wasted effort and potential feature parity gaps. The V1 client logic is sound; V2 should adapt/port it rather than reinvent it, or explicitly wrap it.

*   **V1 Infrastructure/Application overlap:**
    *   *Why:* Orchestration logic is split between `application/pipeline` (CLI) and `infrastructure/cloud/functions` (GCP).
    *   *Risk:* "Works on my machine" but fails in cloud. Logic changes must be applied in two places.

*   **Component Isolation (ML):**
    *   *Why:* The `ml/` folder sits outside the main application structure in V1 and isn't mentioned clearly in the V2 plan.
    *   *Risk:* Advanced features like "Winner Prediction" might get lost in the migration if not explicitly mapped to V2's `analysis` or `pipeline` layers.

## 5. Refactoring Roadmap

This roadmap focuses on enabling the V2 transition while maintaining stability.

1.  **Extract Shared Kernel (High Priority)**
    *   *Scope:* `src/causaganha/domain/scoring` -> `src/causaganha/common/scoring` (or similar).
    *   *Goal:* Create a clean, dependency-free module for the OpenSkill logic that both V1 and V2 can import without V2 touching V1's `domain`.
    *   *How:* Move the files, update imports in V1.

2.  **Port PJe Client to V2 (Medium Priority)**
    *   *Scope:* `src/causaganha/infrastructure/integrations/pje/` -> `src/causaganha/v2/api/`.
    *   *Goal:* Jumpstart V2 development by adapting the existing working client instead of rewriting it.
    *   *How:* Copy the V1 client to V2, refactor it to use V2's new Pydantic models (which use strict snake_case aliases), and ensure it fits the new `httpx` setup.

3.  **Implement V2 Storage Layer (High Priority)**
    *   *Scope:* `src/causaganha/v2/storage/`.
    *   *Goal:* establish the Ibis connection and schema early to unblock pipeline development.
    *   *How:* Follow the V2 plan to implement `connection.py` and `schema.py`.

4.  **Freeze V1 (Policy)**
    *   *Scope:* `src/causaganha/{application,domain,infrastructure}`.
    *   *Goal:* Prevent new features in V1.
    *   *How:* Add a `DEPRECATED` notice to V1 module docstrings.

## 6. Updated Target Architecture (Conceptual)

After the transition, the architecture should look like this:

```text
src/
  causaganha/
    common/          # Shared logic (Scoring, Utils) - Zero dependencies on app
    v2/
      api/           # PJe Client (pure httpx + pydantic)
      storage/       # Ibis + DuckDB (Data access)
      analysis/      # Pydantic AI Agents (Pure business logic)
      pipeline/      # Orchestrators (Collect -> Store -> Analyze -> Score)

    # Legacy V1 folders (domain, application, infra) are deleted or archived.
```

**Cross-cutting Concerns:**
*   **Logging:** Use `structlog` (as planned) configured at the entry point (CLI/Cloud Function), passed down implicitly or via context.
*   **Config:** Pydantic BaseSettings in `v2/config.py`.

## 7. Guardrails & Conventions

1.  **Strict Isolation:** Code in `src/causaganha/v2/` **MUST NOT** import from `src/causaganha/{domain, application, infrastructure, ml}`. It may only import from `src/causaganha/common` (shared kernel).
2.  **Model Separation:** V2 API models (`v2.api.models`) must be distinct from V2 Analysis models (`v2.analysis.models`) to allow independent evolution of the external API contract and the internal analytical needs.
3.  **TDD First:** As per the plan, no V2 code should be written without a failing test in `tests/v2/`.
4.  **Ibis for Data:** All data transformations in V2 pipelines must use `ibis` expressions, not raw SQL strings (except for explicit `ON CONFLICT` optimized writes) or Pandas DataFrames.
