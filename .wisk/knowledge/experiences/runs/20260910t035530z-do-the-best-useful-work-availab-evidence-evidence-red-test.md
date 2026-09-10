---
type: "RunEvidence"
id: "run-evidence/20260910t035530z-do-the-best-useful-work-availab/evidence-red-test"
run: "runs/20260910T035530Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/djen_backup/test_dead_config_fields_removed.py, run via 'python -m pytest tests/djen_backup/test_dead_config_fields_removed.py -q' against unmodified src/djen_backup/{engine,service}.py"
summary: "Both assertions failed: dataclasses.fields(SyncConfig) and dataclasses.fields(PipelineRunConfig) both included 'skip_if_mostly_complete' -- confirming the dead fields were still present before the fix."
goal: "goal-remove-dead-config-flags"
---

# RunEvidence
