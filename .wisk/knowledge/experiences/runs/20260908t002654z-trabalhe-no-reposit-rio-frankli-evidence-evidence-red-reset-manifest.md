---
type: "RunEvidence"
id: "run-evidence/20260908t002654z-trabalhe-no-reposit-rio-frankli/evidence-red-reset-manifest"
run: "runs/20260908T002654Z-trabalhe-no-reposit-rio-franklinbaldo-causaganha"
kind: "test_red"
reference: "tests/djen_backup/test_service_reset.py"
summary: "Both new tests fail before the fix: test_reset_clears_djen_raw_so_entry_is_no_longer_terminal and test_reset_all_clears_djen_raw_across_tribunals assert entry.djen_raw == '' after reset_manifest(); pytest showed AssertionError: assert '404' == '' and assert '200' == '' -- confirming reset_manifest left djen_raw untouched, so interpret_djen_raw(entry.djen_raw) kept returning a terminal verdict ('absent'/'available') post-reset."
---

# RunEvidence
