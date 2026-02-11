# causaganha Roadmap

## 🎯 Strategic Goals
The primary mission of **causaganha** is to democratize access to Brazilian judicial data through robust archival and intelligent analysis. Our immediate strategic focus is:

1.  **Complete the Data Backfill**: Eliminate the 50k+ pending items backlog to ensure a comprehensive historical record.
2.  **Stabilize Operations**: Ensure the collection pipeline can reliably monitor 91+ tribunals without gaps.
3.  **Enhance Data Accessibility**: Transform archived data into queryable assets for researchers and the public.
4.  **Operationalize AI Analysis**: Move from experimental to production-grade AI analysis for decision outcomes.

## 📊 Current State Summary

**Status**: Alpha / Backfill Mode
**Backlog**: ~51,663 items pending (~21.5h ETA at current rate)

-   **Strengths**:
    -   **Robust Archival**: Reliable integration with Internet Archive ensures permanent, free storage.
    -   **Modern Stack**: Use of DuckDB and Ibis allows for powerful, local-first analytics and easy portability.
    -   **Clean Pipeline Architecture**: The separation of `collect`, `consolidate`, and `embed` steps via `scripts/pipeline/run.py` is sound and functional.
    -   **Pydantic AI Integration**: The analysis module uses modern, type-safe AI interaction patterns.

-   **Weaknesses**:
    -   **Backfill Velocity**: The current collection rate (~2,400 items/h) is insufficient to clear the backlog quickly while keeping up with new data.
    -   **CLI Monolith**: The `src/causaganha/cli/__init__.py` "God File" impedes maintainability and multi-developer contribution.
    -   **Code duplication/Confusion**: Split between `scripts/pipeline/` (archival ops) and `src/causaganha/pipeline/` (internal logic) creates cognitive load.
    -   **Observability**: While the dashboard exists, it relies on a JSON file (`run-stats.json`) updated by the pipeline, which may trail real-time status during long backfills.

-   **Technical Debt**:
    -   **Documentation Rot**: `ARCHITECTURE_REPORT_V2.md` and other docs reference non-existent files.
    -   **Mixed Abstractions**: Some repositories mix raw SQL with Ibis expressions.
    -   **Testing Gaps**: While unit tests exist, end-to-end integration tests for the full `collect -> consolidate -> catalog` flow are limited.

## 🚀 Roadmap (Prioritized)

### Phase 1: Critical Fixes & Stability (Next 2 weeks)
**Goal:** Accelerate backfill and ensure 100% data capture reliability.

- [ ] **Optimize Collection Concurrency**
    -   **Why**: To clear the 51k+ backlog faster than 21 hours.
    -   **Impact**: Reduces time-to-complete for backfill; ensures system can catch up if paused.
    -   **Effort**: Small (tuning `workers` in `collect.py` and `pipeline.yml`).
    -   **Dependencies**: Monitor IA API rate limits.

- [ ] **Enhance Resilience of `collect.py`**
    -   **Why**: Transient network errors should not crash the pipeline or cause data gaps.
    -   **Impact**: Higher success rate for unattended runs.
    -   **Effort**: Medium (Improve retry logic, better error categorization).

- [ ] **Validate Dashboard Accuracy**
    -   **Why**: Ensure `run-stats.json` accurately reflects the *current* state of the backfill, not just the last completed run.
    -   **Impact**: Trusted monitoring for operations.
    -   **Effort**: Small.

### Phase 2: Core Features & Refactoring (Next month)
**Goal:** Pay down technical debt to enable faster feature development.

- [ ] **Decompose CLI Monolith**
    -   **Why**: `src/causaganha/cli/__init__.py` is too large and mixes concerns.
    -   **Impact**: Easier maintenance, enabling new commands without risk of breaking existing ones.
    -   **Effort**: Medium (Refactor into `src/causaganha/cli/commands/`).

- [ ] **Unify Pipeline Logic**
    -   **Why**: Confusion between `scripts/` and `src/`.
    -   **Impact**: Clearer codebase navigation. `scripts/` should purely be entry points calling logic in `src/`.
    -   **Effort**: Medium.

- [ ] **Expand Catalog Views**
    -   **Why**: Researchers need more than just raw tables.
    -   **Impact**: Immediate value for data consumers.
    -   **Effort**: Medium (Add views for "active lawyers", "win rates", etc., in `catalog/creator.py`).

### Phase 3: Advanced Features (Next quarter)
**Goal:** Deliver unique insights via AI and Scoring.

- [ ] **Productionize AI Analysis**
    -   **Why**: Turning raw text into structured outcomes is the core value prop.
    -   **Impact**: Enables the "Win Rate" metric.
    -   **Effort**: Large (Cost optimization, batch processing, ground truth validation).

- [ ] **Tune OpenSkill Scoring**
    -   **Why**: Ratings must be statistically valid and stable.
    -   **Impact**: Credible lawyer rankings.
    -   **Effort**: Large (Backtesting against historical data).

- [ ] **Semantic Search API**
    -   **Why**: Enable "find similar cases" functionality.
    -   **Impact**: High value for legal research.
    -   **Effort**: Medium (leverage existing `embed.py` and Jina/Gemini).

### Phase 4: Future Vision (6+ months)
**Goal:** Scale and decentralize.

- [ ] **Decentralized Collection Nodes**: Allow community members to run scraper nodes to distribute load/risk.
- [ ] **Public Data API**: Host a Datasette or similar instance for instant public querying without downloading Parquet.
- [ ] **Law Firm Integration**: Direct export formats for major legal CRM systems.

## 🔧 Technical Improvements Backlog
-   **Standardize Ibis Usage**: Remove raw SQL from repositories where possible.
-   **Strict Typing**: Increase MyPy coverage to strict mode.
-   **Dependency pruning**: Remove unused dependencies to speed up CI/CD.

## 📝 Documentation Needs
-   **Consolidate Architecture Docs**: Remove old reports, keep `ARCHITECTURE_REPORT_FINAL.md` updated.
-   **Developer Guide**: Add a clear "How to add a new command" guide after CLI refactor.
-   **Data Dictionary**: detailed schema documentation for the Parquet files.

## 🧪 Testing Gaps
-   **E2E Pipeline Test**: A test that runs `collect` -> `consolidate` -> `catalog` on a small mock dataset to verify the full flow.
-   **IA Upload Mock**: Better mocking of Internet Archive S3 API to avoid hitting real endpoints during tests.

## 💡 Innovation Ideas
-   **"Judge Profiler"**: Use the same data to analyze judge tendencies, not just lawyers.
-   **Real-time Alerts**: Notify lawyers when a new decision mentions them (push notifications).
