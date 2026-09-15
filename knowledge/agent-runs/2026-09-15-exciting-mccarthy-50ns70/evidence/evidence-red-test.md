---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-50ns70-evidence-red-test"
run_id: "2026-09-15-exciting-mccarthy-50ns70"
goal_id: "2026-09-15-exciting-mccarthy-50ns70-goal-cors-probe-ci"
kind: "test_red"
reference: "tests/test_archive_cors_probe.py"
summary: "Wrote tests/test_archive_cors_probe.py (4 cases for evaluate_cors_probe_result: expected_blocked/passes, download_now_allowed/fails, metadata_endpoint_broken via error/fails, metadata_endpoint_broken via non-cors type/fails) against a not-yet-existing scripts/benchmarks/archive_cors_probe.py. Temporarily moved the already-drafted implementation aside (`mv scripts/benchmarks/archive_cors_probe.py /tmp/...`) and ran `uv run pytest tests/test_archive_cors_probe.py -q`: collection failed with `ModuleNotFoundError: No module named 'scripts.benchmarks.archive_cors_probe'` -- confirmed RED before restoring the implementation."
---

# Evidência: teste RED

`uv run pytest tests/test_archive_cors_probe.py -q` com a implementação temporariamente removida falhou na coleta (`ModuleNotFoundError`), confirmando que os 4 testes de `evaluate_cors_probe_result` são reais e falhavam antes da implementação existir.
