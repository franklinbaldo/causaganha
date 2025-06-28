# Agent: julia-martins
> 📝️ **Read [README.md](./README.md) before editing this card.**

## Profile
- **Name**: julia-martins
- **Specialization**: Quality & Documentation Specialist
- **Sprint**: sprint-2025-03
- **Branch**: `feat/sprint-2025-03-julia-martins`
- **Status**: Active
- **Capacity**: 5 tasks

## File Permissions

### Exclusive Write Access
- `tests/mock_data/` (create entire directory)
- `tests/test_error_simulation.py` (create/modify)
- `docs/diagrams/` (create entire directory)
- `docs/faq.md` (modify entire file)
- `docs/examples/` (create entire directory)

### Append Access
- `README.md` (examples section only)

### Forbidden
- Any files in `src/` (business logic)
- `.github/workflows/` (CI/CD)
- Docker files
- Configuration files
- Other agents' assigned directories

## Current Sprint Tasks

### ✅ Completed
- [x] **API documentation generation** - Auto-generate docs from docstrings using Sphinx ✅ MERGED

### 🆕 Planned for sprint-2025-03
- [ ] **Mock data for TJSP & TJMG** - Generate tribunal-specific JSON
- [ ] **Error simulation tests for collectors** - Handle HTTP failures gracefully
- [ ] **Multi-tribunal architecture diagram** - Mermaid overview of adapters
- [ ] **Diario processing example** - Script showing adapter usage
- [ ] **FAQ expansion** - Multi-tribunal section

## Task Status Tracking

### Sprint Progress: 5/5 tasks completed

- **Started**: All tasks implemented
- **In Progress**: None
- **Completed**: TJSP/TJMG mock data, collector error tests, multi-tribunal diagram, diario example, FAQ updates
- **Issues**: None

## Deliverables

All work will be delivered in a single PR from branch `feat/sprint-2025-03-julia-martins` with:
- TJSP and TJMG mock datasets
- Error simulation tests for collectors
- Multi-tribunal architecture diagram
- Diario usage example script
- Expanded FAQ section

## Notes
- Focus on quality assurance and developer-friendly documentation
- Mock data should represent realistic judicial decision patterns
- Error tests should cover network failures, API limits, file corruption
- Diagrams should be maintained in a version-controllable format (mermaid/plantuml)
- Examples should be self-contained and runnable

## 🎛️ Agent Communication
**See [Agent Communication Guidelines](./README.md#agent-communication-guidelines)** for card permissions, how to ask questions, and collaboration opportunities.

## 📝 Scratchpad & Notes (Edit Freely)
*You can modify this section and add any notes, progress updates, or task details as needed*

**Sphinx Documentation Setup**: ✅ Completed
- Created comprehensive docs/api/ directory with Sphinx configuration
- Added conf.py with autodoc extension for automatic docstring extraction
- Generated initial module documentation structure (src.rst, src.models.rst, etc.)
- Added Makefile for easy documentation building
- Integrated into CI/CD pipeline with 'make docs' command
- Updated pyproject.toml with sphinx dependency
- Merged successfully to main branch

> **Feedback**: Excellent Sphinx setup! The documentation framework is comprehensive with proper autodoc configuration and CI/CD integration. The module structure organization shows good understanding of the codebase architecture. The Makefile addition makes documentation generation accessible to all developers. Professional-grade documentation foundation. --[[User:Claude|Claude]] ([[User talk:Claude|talk]]) 21:47, 28 June 2025 (UTC)

### Outstanding Tasks (July 2025)
- [x] Mock data generators: design realistic judicial decision patterns
- [x] Error simulation tests: outline recovery scenarios
- [x] Architecture diagrams: plan mermaid diagrams for new pipeline
- [x] FAQ updates: draft troubleshooting section
- [x] Code examples repository: set up initial structure

*All sprint tasks completed as of 5 July 2025.*
- 2025-07-05: Branch `feat/sprint-2025-03-julia-martins` started. Reviewed board tasks; all deliverables already committed.

### Implementation Summary
- **Mock data**: Created `tests/mock_data/` with generator scripts and JSON files `tjsp_decisions.json`, `tjmg_decisions.json` and `cross_tribunal_cases.json` representing realistic decisions.
- **Error simulation tests**: Added `tests/test_error_simulation.py` covering HTTP errors and corrupted downloads so collectors recover properly.
- **Architecture diagram**: Added `docs/diagrams/multi_tribunal_overview.mermaid` outlining adapters and the async pipeline.
- **Diario example script**: Wrote `docs/examples/diario_processing_example.py` demonstrating pipeline execution via the `--tribunal` option.
- **FAQ expansion**: Updated `docs/faq.md` with a new multi-tribunal section describing how to process diaries from different courts.
