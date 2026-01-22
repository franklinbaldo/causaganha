# Roadmap & Milestones

The development roadmap for rebooting CausaGanha is structured in progressive phases. Each phase builds on the previous, from getting the core system stable to expanding its scope and adding advanced capabilities.

## Phase 1: Foundation Stabilization (✅ Completed in v1)

**Goal:** Fix critical issues in the base system and establish a stable foundation.

*   **Database Integration Fix:** Switch to DuckDB and ensure all data persists correctly.
    *   **Milestone:** All CLI commands function end-to-end with the new DB, and initial schema (about 20 tables) is in place. Achieved with DuckDB storing case data, and Internet Archive sync working for backups.
*   **Test Suite Stabilization:** Resolve failing tests and ensure core pipeline logic is reliable.
    *   **Milestone:** 100% of pipeline tests passing (no known bugs in collect/archive/analyze/score flows). As part of this, the downloader was improved and integrated with IA, and total passing tests exceeded 100.
*   **System Integration Resolution:** (In progress at the tail of Phase 1) Clean up any mismatches between components.
    *   **Milestone:** Unified CLI interface and consistent argument handling across commands. For example, standardize how date ranges and court codes are passed to pipeline, and ensure the CLI properly coordinates the new v2 modules. This lays ground for adding new features without breaking existing commands.

*(Status: Phase 1 was effectively the wrap-up of v1 and preparation for v2. It concluded with a solid base – database and basic pipeline fixed – so the team can confidently extend the system.)*

## Phase 2: Infrastructure & Core V2 Build (Weeks 3-4 of reboot)

**Goal:** Modernize the architecture and implement new data handling for v2. This phase is about building internals rather than expanding to new courts yet.

*   **2A. PJe Metadata Integration:** Implement the new Diário Dataclass/Metadata system.
    *   **Milestone:** Use PJe API to retrieve structured case data, replacing the old PDF scraping. Introduce Pydantic models for cases and ensure the pipeline can collect via API for at least TJRO. This provides a unified interface to add other tribunals later.
*   **2B. DuckDB + dbt Migration (DTB):** Migrate data management to a dbt-duckdb workflow.
    *   **Milestone:** Design a robust DuckDB schema (raw data, staging, marts) and use dbt for transformations and quality tests. By end of this, the database will have improved data quality checks and can support analytical queries more efficiently. This includes setting up staging tables for raw API data and derived tables for lawyer stats.
*   **2C. Archive Strategy Refactor:** Refine how files are archived to IA.
    *   **Milestone:** Switch to the single master IA item approach where all PDFs from all courts go into one collection. Implement incremental metadata updates on IA (so that analysis results are also reflected in IA, e.g. uploading a JSON summary for each batch of analyses). Also unify CLI commands: instead of separate archive processes per court or mode, one command handles all with consistent options. By end of Phase 2, archiving a new court’s data or a new day’s PDFs should be one straightforward command, and the IA structure should be confirmed working.

*(Planned Deliverables: A fully working v2 pipeline for one court (TJRO) using API data and new DB. By this phase, the system should be ready for end-to-end integration tests with real data, proving that the refactored components work together.)*

## Phase 3: Expansion (Weeks 5-8)

**Goal:** Scale the system to support multiple courts and introduce systems for maintainability as the project grows.

*   **Multi-Tribunal Support:** Extend the architecture to handle multiple courts in parallel.
    *   **Milestone:** Integrate at least 2-3 additional tribunals (e.g., TJSP, TJMG) by building on the new adapter structure. This involves adding configuration or adapters for each new court’s API endpoints (if needed) and ensuring the pipeline can loop through multiple `--courts` in one run. Success is measured by having a generalized framework where adding a new court is mostly data configuration, not new code.
*   **LLM Prompt Versioning System:** Develop a versioning strategy for AI prompts and analysis logic.
    *   **Milestone:** Every change to how the LLM analyzes text (e.g., prompt tweaks) gets a version tag or hash. The system will keep track of which prompt version was used for each analysis record. This ensures reproducibility and allows re-processing cases if a better prompt is developed. A CI check might enforce prompt files to carry version identifiers.
*   **Performance Optimization:** As the data volume grows, implement async pipeline optimizations and better concurrency control.
    *   **Milestone:** Achieve smooth parallel processing of downloads and AI calls without hitting rate limits or memory bottlenecks (e.g., use semaphores to limit concurrency for API or LLM calls). Also, ensure the system can handle 3+ courts running daily without manual intervention (monitoring hooks may be added here).

*(Planned Deliverables: By end of Phase 3, CausaGanha is not just a TJRO project but supports a broader set of courts, making national-level analyses possible. The technical underpinnings (like prompt management and concurrency) are prepared for even further scale.)*

## Phase 4: Advanced Features & Hardening (Weeks 9+)

**Goal:** Enhance analytics capabilities and polish the system for a public launch or beta, including user-facing components and quality improvements.

*   **Stabilization & Quality Improvements:** There are several “hardening” sub-plans to address reliability and quality across the system. This includes improving data validation (implementing a validation layer that checks for inconsistencies or missing fields in collected data) and error handling/logging throughout (perhaps introducing structured logging via structlog and more graceful exception handling) to make troubleshooting easier. Also, enhance the IA interaction robustness (e.g., better retry logic on uploads, checksum verifications) and the testing framework (adding more integration tests, fuzz tests for different courts).
    *   **Milestone:** The system runs for weeks without uncaught errors, and logs/metrics show stable operation. Test coverage should rise towards 80% or more on critical modules.
*   **Advanced Analytics Features:** Build on the collected data to provide deeper insights. For example, implement analytical reports or new metrics: lawyer win-rate by case type, court efficiency metrics, trending legal issues, etc. This might involve additional data modeling in DuckDB or integrating a small analytics engine.
    *   **Milestone:** Provide at least one new analytical output beyond the basic rankings – e.g., a summary report or the ability to query the most frequent winners by category (which could be exposed via the dashboard or as a generated report in docs).
*   **Additional LLM Provider Support:** Add support for alternative LLMs or an ensemble approach. This reduces reliance on a single provider (Gemini).
    *   **Milestone:** The analyzer can be configured to use different AI backends (OpenAI, local model, etc.) via the Pydantic-AI interface with minimal changes. This might include implementing fallbacks if one API fails or cost-optimization strategies (use a cheaper model for simple cases, a powerful model for complex ones).
*   **OpenSkill Refinements:** Review the rating model with more data. Possibly adjust parameters or incorporate decay over time (if lawyers become inactive).
    *   **Milestone:** A refined rating algorithm documented and implemented (for instance, after analysis, we decide to factor in partial credit for cases with multiple lawyers or implement a time decay on ratings). Any changes would be versioned so older ratings can be reproduced.
*   **Web Dashboard/UI:** Develop a simple web dashboard to make the data accessible to non-technical users. The plan might favor a Streamlit app for simplicity or a FastAPI + lightweight frontend for more control.
    *   **Milestone:** A basic dashboard running (locally or deployed) where one can see overall stats (e.g., total cases, number of courts, top N lawyers) and maybe search for a lawyer to view their win/loss record. This is optional for an initial launch but highly desirable for broader impact.

*(Planned Deliverables: Phase 4 concludes with CausaGanha being a robust platform ready for open beta – covering multiple jurisdictions, with strong reliability, and offering user-friendly access to the insights. All major technical debt from earlier phases should be resolved here too.)*
