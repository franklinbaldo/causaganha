---
type: "RunEvidence"
id: "run-evidence/20260909t012625z-do-the-best-useful-work-availab/evidence-red-green-dead-helper-removed"
run: "runs/20260909T012625Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "src/causaganha/consolidate/candidates.py (35 lines deleted); tests/consolidate/test_candidates_module_surface.py (new, 1 case)"
summary: "RED: new test_dead_tribunal_year_helper_was_removed failed with AssertionError (hasattr True) while tribunal_years_needing_consolidation_from_ia still existed. GREEN: same test passes after deleting the function (repo-wide grep confirmed zero callers/tests beforehand). Diff is a pure deletion, no behavior change to the live dates_needing_consolidation_from_ia sibling."
goal: "run-goals/20260909t012625z-do-the-best-useful-work-availab/goal-remove-dead-tribunal-year-helper"
---

# RunEvidence
