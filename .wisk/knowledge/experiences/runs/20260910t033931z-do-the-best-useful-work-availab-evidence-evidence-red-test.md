---
type: "RunEvidence"
id: "run-evidence/20260910t033931z-do-the-best-useful-work-availab/evidence-red-test"
run: "runs/20260910T033931Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/djen_backup/test_upload_only_no_djen_check.py::test_upload_only_never_checks_djen_for_unknown_entries, run via 'python -m pytest tests/djen_backup/test_upload_only_no_djen_check.py -q -s' against unmodified src/djen_backup/engine.py"
summary: "Seeded a SyncManifest with one entry (TJSP/2024-01-03, djen_status='', djen_raw='', ia_status='' -- availability not yet known) and ran engine.run_pipeline with upload_only=True, monkeypatching engine_module.get_caderno_url to record any call and raise. Failed as expected: AssertionError: assert {'checked': True} == {'checked': False} -- confirming the unmodified pipeline still probes DJEN for an unknown entry even under upload_only=True, contradicting the 'Upload already-discovered available entries (backlog drain)' contract documented in CLAUDE.md and the upload() subcommand's own docstring."
goal: "goal-upload-only-no-djen-check"
---

# RunEvidence
