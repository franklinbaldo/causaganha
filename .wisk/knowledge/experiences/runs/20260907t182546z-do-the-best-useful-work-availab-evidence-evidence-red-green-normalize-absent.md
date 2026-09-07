---
type: "RunEvidence"
id: "run-evidence/20260907t182546z-do-the-best-useful-work-availab/evidence-red-green-normalize-absent"
run: "runs/20260907T182546Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/djen_backup/test_segments.py::test_apply_event_resets_absent_with_empty_raw_to_unknown"
summary: "RED: test written first, confirmed failing with AssertionError: assert ('absent', '') == ('', '') -- apply_event created a new entry with djen_status='absent'/djen_raw='' verbatim, no downgrade. GREEN: after adding a third normalization guard to SyncManifest._normalize_event (src/djen_backup/manifest.py) -- 'if djen_status == absent and not djen_raw: djen_status = \"\"' -- mirroring the existing guard in the legacy _load_manifest_line CSV loader. Full tests/djen_backup/ suite (105 tests) passes after the fix with no regressions to the sibling contradiction-normalization test (confirmed/absent+200)."
goal: "run-goals/20260907t182546z-do-the-best-useful-work-availab/goal-fix-absent-empty-raw-normalization"
---

# RunEvidence
