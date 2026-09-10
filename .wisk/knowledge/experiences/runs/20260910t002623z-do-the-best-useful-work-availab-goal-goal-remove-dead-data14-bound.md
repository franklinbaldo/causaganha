---
goal: "Delete the dead data14_bound helper from src/datajud/models.py and its __all__ export."
id: "run-goals/20260910t002623z-do-the-best-useful-work-availab/goal-remove-dead-data14-bound"
kind: "task-advance"
rationale: "A background Explore-agent audit swept deployment/relay-cf, tjro_juris, stj_acordaos, web/src/lib/data, remaining .qmd contracts, and several Svelte components -- all previously unaudited by today's ~20 prior automated rounds -- and found no new live correctness bug (independently re-verified: repo-wide grep confirms zero callers of data14_bound outside its own definition and unit test; src/datajud/client.py never builds a dataAjuizamento range query with it, and has no duplicated inline equivalent that could drift). This exact dead-code lead was identified and explicitly deprioritized by run 20260908T202452Z's own RunDecision in favor of a higher-value bug that round; today, after a genuinely thorough re-audit turned up nothing better, it is the best available real advance: removing unused, untestable-in-practice surface area, matching this repository's established dead-code-deletion pattern (PR #1332's coverageInsights.ts Catalog surface, PR #1354's candidates.py tribunal-year helper)."
run: "runs/20260910T002623Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "tests/datajud/test_datajud_models_module_surface.py::test_dead_data14_bound_helper_was_removed fails RED while data14_bound still exists in src/datajud/models.py's __all__/module namespace, and passes GREEN once it is deleted from both the function body and __all__ (and its own now-orphaned unit tests in tests/datajud/test_datajud_models.py are removed). Full pytest suite, ruff check, and ruff format --check stay green; no other module imports data14_bound so no other file needs edits."
type: "RunGoal"
---

# RunGoal
