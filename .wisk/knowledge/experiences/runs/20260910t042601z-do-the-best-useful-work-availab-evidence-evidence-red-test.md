---
type: "RunEvidence"
id: "run-evidence/20260910t042601z-do-the-best-useful-work-availab/evidence-red-test"
run: "runs/20260910T042601Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/djen_backup/test_download_worker_fail_fast.py::test_failed_download_with_fail_fast_sets_abort, run via 'uv run pytest tests/djen_backup/test_download_worker_fail_fast.py -v' against unmodified src/djen_backup/engine.py"
summary: "RED: assert abort_event.is_set() failed (False) after run_pipeline ran a monkeypatched-failing download to completion; log showed 'download_failed' followed by the pipeline continuing until 'deadline_reached_aborting' fired at the 5s deadline instead of stopping immediately on the first error, confirming fail_fast=True is silently ignored on the download path."
goal: "goal-fix-download-fail-fast"
---

# RunEvidence
