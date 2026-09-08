---
goal: "Fix scripts/backfill_probe.py's _probe_one, which classifies live_raw from the bare DJEN HTTP status code and so reports a genuinely-absent 200-Sem-comunicações caderno as live_raw='200' (available) instead of 'no_publications' (absent), reproducing the historical ~79K-row false-available bug inside the diagnostic tool whose entire purpose is to catch this class of manifest/live drift."
id: "run-goals/20260908t172434z-do-the-best-useful-work-availab/goal-fix-backfill-probe-classification"
kind: "task-advance"
rationale: "The issue backlog (17, all environment-blocked ML/segmenter or product issues out of scope for this session) and the PR queue (empty) were both re-verified fresh per the prior round's next_move. A background Explore-agent audit swept src/causaganha_mcp, djen.py, archive.py, engine.py, retry.py, __main__.py, scripts/, and the three legacy Svelte islands (areas not yet covered by today's many prior audit rounds) and found this concrete, verified defect: _probe_one classifies live_raw purely from resp.status_code, never inspecting the JSON body, while every other DJEN caller in this codebase (engine.py's _classify_djen_status, djen_backup/probe.py's _probe_one, scripts/drain_unknowns.py) derives the raw code from get_caderno_url, which raises DJENNotFoundError(status_code=200) for 'Sem comunicações' precisely so callers never record a bare '200'."
run: "runs/20260908T172434Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "A new RED test (tests/test_backfill_probe_classify.py::test_probe_one_reports_no_publications_for_200_sem_comunicacoes) that mocks the DJEN proxy returning HTTP 200 with body {'status': 'Sem comunicações'} currently fails (asserts live_raw=='no_publications', gets '200'); after the fix it passes, alongside sibling tests for the available-200 and 403-rate-limited cases, and the full pytest suite stays green."
type: "RunGoal"
---

# RunGoal
