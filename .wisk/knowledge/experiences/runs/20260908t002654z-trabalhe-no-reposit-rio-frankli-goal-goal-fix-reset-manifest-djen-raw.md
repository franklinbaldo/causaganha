---
type: "RunGoal"
id: "run-goals/20260908t002654z-trabalhe-no-reposit-rio-frankli/goal-fix-reset-manifest-djen-raw"
run: "runs/20260908T002654Z-trabalhe-no-reposit-rio-franklinbaldo-causaganha"
kind: "task-advance"
goal: "Fix djen-backup's 'reset' CLI command so it actually forces a DJEN recheck instead of silently no-op'ing"
rationale: "src/djen_backup/service.py's reset_manifest() clears ia_status/djen_status/updated_at but never clears djen_raw. engine.py's check-priority builder (run_pipeline, engine.py:417-422) explicitly derives 'terminal' status from djen_raw (not djen_status) specifically so stale djen_status can't hide a re-checkable entry -- but that same logic means reset_manifest's surviving djen_raw silently re-derives the same terminal available/absent verdict the user was trying to clear, so the reset CLI command (whose own docstring promises 'clears djen_status and ia_status' to force a recheck) is a no-op for exactly the entries (djen_raw='200'/'404'/etc, i.e. already-terminal) an operator would actually run it against. Zero existing test coverage for reset_manifest or the reset CLI command. This is a live, demonstrable defect, not speculative hardening, matching this loop's established TDD pattern (probe.py 403, circuit_breaker.py x3)."
success_signal: "A new failing test (RED) reproduces the no-op via interpret_djen_raw(reset entry's djen_raw) still returning a terminal verdict after reset_manifest(); after clearing djen_raw in reset_manifest, the same test passes (GREEN); full pytest -q, ruff check, ruff format --check stay green; a PR is opened and driven to green/mergeable."
status: "active"
---

# RunGoal
