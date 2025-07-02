# TODO

This file summarizes the next implementation steps extracted from **docs/plans/MASTERPLAN.md**. Each item links to the relevant plan so developers can quickly locate the full context. Review this file before starting any feature work.

## Immediate Priorities

- [ ] **Complete System Integration** (`system-integration-resolution.md`)
  - Finish consolidating the pipeline and standardize CLI arguments.
  - Integrate extract/analyze stages with real data processing.
  - Ensure unified CLI and database synchronization are fully functional.

- [ ] **Expand Agent Sprint**
  - Coordinate 18 specialized agents as defined in `.agents/`.
  - Track progress via the agent registry for sprint `sprint-2025-03`.

- [ ] **Prepare Phase 2**
  - Begin work on the Diario dataclass foundation and DTB migration.
  - Maintain >140 passing tests while coverage goals increase.

## Phase 2 – Infrastructure

- [ ] **Diario Dataclass Foundation** (`diario-class.md`)
  - Create a unified `Diario` interface for all tribunals.
  - Implement a TJRO adapter using the existing system.

- [ ] **DTB Database Migration** (`dtb.md`)
  - Move to a dbt-duckdb based schema with staging and marts layers.
  - Requires the dataclass system to be in place.

- [ ] **Archive Strategy Refactor** (`refactor_archive_command.md`)
  - Adopt a single master Internet Archive item with incremental metadata.
  - Unify archive commands across tribunals.

## Phase 3 – Expansion

- [ ] **Multi-Tribunal Collection** (`multi_tribunal_collection.md`)
  - Support at least three tribunals with an extensible collector framework.
  - Depends on the archive refactor and dataclass foundation.

- [ ] **Prompt Versioning System** (`prompt_versioning_strategy.md`)
  - Introduce content-hash based prompt names and CI checks.
  - Requires stable system and LLM integration.

## Phase 4 – Advanced Features

- [ ] **Stabilization Plans**
  - Implement data validation layers, improved error handling, and IA robustness.
  - Optimize async operations and improve the downloader module.

- [ ] **Advanced Features**
  - Add support for new LLM providers and refine the OpenSkill model.
  - Develop advanced analytics capabilities and a web dashboard.

---

Refer to `docs/plans/MASTERPLAN.md` for full details and timelines.
