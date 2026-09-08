---
goal: "scripts/drain_unknowns.py's _classify() must return the 'no_publications' sentinel (never bare '200') when get_caderno_url raises DJENNotFoundError(status_code=200) for DJEN's 'Sem comunicações' response, matching engine.py's _classify_djen_status."
id: "run-goals/20260908t083545z-do-the-best-useful-work-availab/goal-fix-drain-unknowns-200-bug"
kind: "task-advance"
rationale: "drain_unknowns.py (wired to the live scheduled drain-unknowns.yml workflow) silently reproduces the exact historical ~79K-row false-'available' bug CLAUDE.md warns about: it returns str(exc.status_code) unconditionally for DJENNotFoundError, so a 200-with-no-download-URL is recorded as raw='200', which interpret_djen_raw() then derives as 'available' -- manufacturing phantom cadernos in production manifest data every time this script runs."
run: "runs/20260908T083545Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "tests/test_drain_unknowns_classify.py::test_classify_returns_no_publications_for_200_sem_comunicacoes passes (asserts _classify returns 'no_publications' and interpret_djen_raw('no_publications') == 'absent'), the full new test file's other 5 cases (404, 200-success, 403, timeout, network) stay green, and 'uv run pytest -q' plus 'uv run ruff check'/'ruff format --check' remain clean repo-wide."
type: "RunGoal"
---

# RunGoal
