---
goal: "Fix SyncManifest.apply_event to invalidate the warm counts/uploaded-index cache on mutation, per CLAUDE.md's explicit 'invalidate on mutation' invariant"
id: "run-goals/20260907t165419z-do-the-best-useful-work-availab/goal-fix-apply-event-cache-invalidation"
kind: "task-advance"
rationale: "An Explore audit of the djen_backup invariants CLAUDE.md documents found that apply_event (manifest.py) mutates entry.ia_status/djen_status/djen_raw directly with no call to _invalidate_caches(), unlike mark_djen_raw/mark_uploaded/mark_ia_uploaded which all correctly adjust the warm cache inline. It is currently dormant in production because both real call sites (apply_segment_csv, the parquet loader) always invalidate once after a whole batch on a freshly built manifest, but it is a latent trap for any future direct caller (or test) that warms the cache first -- exactly the kind of docstring-vs-code drift this loop has repeatedly found and fixed in past rounds (#1278, #1280)."
run: "runs/20260907T165419Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "tests/djen_backup/test_manifest_counts.py::test_apply_event_invalidates_warm_counts_cache and ::test_apply_event_invalidates_warm_uploaded_index go from RED (assert m.counts().uploaded == 1 fails with 0; assert m.has_uploaded_entries(...) fails with False) to GREEN after apply_event calls _invalidate_caches() on every code path that mutates an entry, with the full pytest suite, ruff check, and ruff format --check staying green."
type: "RunGoal"
---

# RunGoal
