---
type: "RunGoal"
id: "run-goals/20260925t052703z-do-the-best-useful-work-availab/goal-render-queries-artifact-url-validation"
run: "runs/20260925T052703Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Close the remaining gap of handoff-issue-1610-artifact-url-followup: apply the same artifact-URL fetch policy (_validate_artifact_url from causaganha.processos.service, issue #1610) to scripts/render_queries.py::_register_comunicacoes, which interpolates unvalidated arquivo_ia_url values read from indice_processual.parquet directly into a read_parquet([...]) SQL string -- the same injection/redirect class already fixed in service.py and processoCnj.ts. Also land already-ready PR #1625 (security(relay): enforce HTTPS/method/header/size policy, #1609) as a continuity action since it is CI-green and just needed a branch update (triggered this round)."
rationale: "The audit item (b) of handoff-issue-1610-artifact-url-followup was left explicitly open by the prior run; a compromised/malformed indice_processual.parquet could otherwise redirect render_queries.py's read_parquet fetch to an arbitrary host or break out of the SQL string literal via an embedded quote, at Astro build/query-render time -- the same real threat the Python/TS halves of #1610 already closed. Landing PR #1625 advances #1609 to full closure with zero additional review overhead since it is already reviewed-equivalent (CodeQL/GitGuardian/tests all green, no pending review feedback)."
success_signal: "TDD: new failing tests in tests/test_render_queries.py proving a poisoned/injected arquivo_ia_url in indice_processual.parquet reaches _register_comunicacoes's read_parquet SQL unfiltered (RED), then GREEN after _register_comunicacoes validates each URL via the shared policy and drops invalid ones with a warning instead of propagating them; full pytest suite and ruff clean; PR opened. Separately, PR #1625 merged into main with all checks green."
status: "active"
---

# RunGoal
