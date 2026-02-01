# Plan: Absolutist - Sprint 3

**Persona:** Absolutist 💯
**Sprint:** 3
**Created:** 2026-01-26
**Priority:** Medium

## Objectives
<<<<<<< HEAD
Continue the purification of the codebase.

<<<<<<< HEAD
- [ ] **Address CLI Compatibility Layers:** Investigate `src/egregora/cli/main.py` comments regarding "DuckDBStorageManager directly to ensure Ibis compatibility". If the underlying issue is resolved, remove the workaround.
- [ ] **Deep Clean of `input_adapters`:** Check `src/egregora/input_adapters/base.py` for "Note: This is the only adapter interface. The legacy InputSource has been removed." and ensure no artifacts remain.
- [ ] **Review `output_sinks` conventions:** Check for any remaining version tracking or migration compatibility code.
=======
Continuing the mission of simplification, Sprint 3 will focus on deeper structural cleanups and auditing peripheral adapters.

- [ ] **Audit `input_adapters` for Legacy Artifacts:** Ensure that the transition from `InputSource` to the current adapter interface is complete and no "ghost" classes remain.
- [ ] **Review `output_sinks` Compatibility:** Investigate `src/egregora/output_sinks/conventions.py` and other output adapters for migration layers that have served their purpose.
- [ ] **Dead Code Analysis:** Conduct a sweep for unreachable code or unused imports that linters might have missed (or that were ignored).
>>>>>>> origin/pr/2837

## Dependencies
- **Refactor:** Coordination on any large-scale structural changes.

## Context
By Sprint 3, the core configuration and pipeline runner should be stabilized (thanks to Sprint 2 work). This opens the door for cleaning up the "edges" of the system—the input and output adapters—where compatibility shims often hide.

## Expected Deliverables
<<<<<<< HEAD
1.  Refactored CLI database initialization (if possible).
2.  Verified removal of `InputSource` legacy references.
=======
1.  Removal of `att_file` legacy logic in `media.py`.
2.  Removal of `prompts.py` (if approved).
3.  Clean bill of health for input adapters.
>>>>>>> origin/pr/2890
=======
1.  Report on `input_adapters` cleanliness.
2.  Removal of any identified legacy code in `output_sinks`.
3.  Deletion of verified dead code blocks.
>>>>>>> origin/pr/2837

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
<<<<<<< HEAD
| CLI Stability | Medium | High | Manual verification of CLI commands (`egregora write`, `egregora demo`). |
=======
| Removing rarely used but valid adapters | Low | High | Verify usage against production logs or test coverage before removal. |

## Proposed Collaborations
- **With Shepherd:** Ensure that removing "unused" code doesn't reduce test coverage of edge cases that are actually important.
>>>>>>> origin/pr/2837
