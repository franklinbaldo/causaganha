---
type: "RunEvidence"
id: "run-evidence/20260907t165419z-do-the-best-useful-work-availab/evidence-red-green-apply-event"
run: "runs/20260907T165419Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "src/djen_backup/manifest.py apply_event; tests/djen_backup/test_manifest_counts.py"
summary: "RED: added test_apply_event_invalidates_warm_counts_cache and test_apply_event_invalidates_warm_uploaded_index to tests/djen_backup/test_manifest_counts.py, reproducing the audit's live repro (warm counts()/has_uploaded_entries(), call apply_event with ia_status=uploaded, assert the warm value updates) -- both failed as predicted (uploaded stayed 0, has_uploaded_entries stayed False). GREEN: added self._invalidate_caches() to all three mutation paths inside apply_event (new-entry insert, ia_status transition to uploaded, djen_status/djen_raw update) -- both new tests pass, the full tests/djen_backup/ suite (100 tests) passes, and the full repo suite (TRIBUNAL=tjro pytest -q) passes with exit 0. ruff check and ruff format --check stay clean."
goal: "run-goals/20260907t165419z-do-the-best-useful-work-availab/goal-fix-apply-event-cache-invalidation"
---

# RunEvidence
