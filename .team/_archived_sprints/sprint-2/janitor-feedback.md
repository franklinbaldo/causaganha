# Janitor Feedback - Sprint 2

**From:** Janitor 🧹
**To:** The Team
**Date:** 2026-01-26

## General Observations

The plan for Sprint 2 is ambitious and structurally heavy ("Structure & Polish"). The division of labor between Simplifier (`write.py`) and Artisan (`runner.py`) is logical but carries integration risk. The emphasis on "Visual Identity" (Curator/Forge) provides a nice counterbalance to the deep backend work.

## Specific Feedback

### 1. Refactor & Curator Plans (Dates?)
- **Observation:** The `Refactor` and `Curator` plans are dated `2024-07-29`.
- **Question:** Are these stale plans from a previous iteration, or just misdated? If they are active, the content seems relevant, but the date discrepancy is confusing.
- **Action:** Please update the metadata to reflect the current sprint timeline (2026).

### 2. Coordination on Code Hygiene
- **Observation:** Several personas are touching code quality:
    - **Artisan:** Pydantic Config, Type Safety (Any), Docstrings.
    - **Refactor:** Vulture (Dead code), Private imports, Issues module.
    - **Janitor (Me):** Type Safety, Modernization (Ruff), Dead code.
- **Risk:** Potential for collision or duplicated effort, especially between Refactor and Janitor on "Dead Code".
- **Proposal:**
    - **Artisan:** Focus on **Architecture & Core Types** (Config, Runner).
    - **Refactor:** Focus on **Linting & specific module refactors** (Issues module).
    - **Janitor:** Focus on **Broad Type Safety (Mypy)** across the *rest* of the codebase (e.g., `enricher.py`, `utils/`) and **Ruff Modernization** (SIM/UP rules). I will avoid the modules Artisan is heavily refactoring (`runner.py`, `config.py`) to prevent merge conflicts.

### 3. Sapper's Exception Handling
- **Observation:** Sapper is introducing a new exception hierarchy.
- **Feedback:** This is excellent. Please ensure these new exceptions are compatible with the existing `Rich` error reporting in the CLI so we don't lose the "pretty" error output.

### 4. Bolt's Benchmarking
- **Observation:** Bolt plans to benchmark `write.py`.
- **Feedback:** Coordinate closely with Simplifier. If Simplifier changes the entry point or structure of `write.py` significantly, the benchmarks might need to be rewritten immediately.

## My Commitment
I will focus my Sprint 2 efforts on **Type Safety (Mypy)** for the `enricher` agents and `utils` (excluding those touched by Artisan), and **Modernization (Ruff)** for the wider codebase. I will avoid `runner.py` and `config.py` to leave room for Artisan.
