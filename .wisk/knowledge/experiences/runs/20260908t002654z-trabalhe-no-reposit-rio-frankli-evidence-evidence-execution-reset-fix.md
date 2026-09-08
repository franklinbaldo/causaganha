---
type: "RunEvidence"
id: "run-evidence/20260908t002654z-trabalhe-no-reposit-rio-frankli/evidence-execution-reset-fix"
run: "runs/20260908T002654Z-trabalhe-no-reposit-rio-franklinbaldo-causaganha"
kind: "execution"
reference: "src/djen_backup/service.py (reset_manifest) + tests/djen_backup/test_service_reset.py"
summary: "Live execution proved the defect and the fix: reset_manifest(manifest_file, tribunal='TJRO', reset_all=False) against a manifest entry with djen_raw='404' left djen_raw='404' after reset (interpret_djen_raw still returned 'absent'); after adding entry.djen_raw = '' to the reset loop, the same call leaves djen_raw='' (interpret_djen_raw returns '', i.e. no longer terminal) -- matching engine.py's own check-priority logic (engine.py:417-422) that decides whether an entry gets re-checked."
---

# RunEvidence
