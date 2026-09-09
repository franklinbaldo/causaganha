---
type: "RunEvidence"
id: "run-evidence/20260909t212618z-do-the-best-useful-work-availab/evidence-red-green-test"
run: "runs/20260909T212618Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_render_queries.py::test_weekly_pattern_average_excludes_still_in_flight_day"
summary: "RED: failed with 'assert 2.5 == 3.0' against the unfixed weekly_pattern.qmd (settled avg diluted by today's pending_real day). GREEN: passes after weekly_pattern.qmd adopts stats_coverage.qmd's raw_absent/unsettled classification and filters WHERE unsettled = 0 before the per-weekday AVG/COUNT. Full tests/test_render_queries.py suite (54 tests) green."
goal: "run-goals/20260909t212618z-do-the-best-useful-work-availab/goal-weekly-pattern-in-flight"
---

# RunEvidence
