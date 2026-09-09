---
type: "RunGoal"
id: "run-goals/20260909t212618z-do-the-best-useful-work-availab/goal-weekly-pattern-in-flight"
run: "runs/20260909T212618Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Fix web/src/queries/weekly_pattern.qmd so a still-in-flight (pending_real) day never dilutes a weekday's reported average coverage."
rationale: "An Explore-agent audit of previously-unswept .qmd contracts confirmed weekly_pattern.qmd has no settled/unsettled classification at all (unlike stats_coverage.qmd, fixed for the identical failure mode last round) -- every render while any pending-upload row exists for a weekday silently understates that weekday's true average, contradicting the file's own stated purpose ('detectar quedas estruturais'). Reproduced deterministically: a DuckDB repro against the real SQL showed avg=2.6 vs the true settled 3.0."
success_signal: "tests/test_render_queries.py::test_weekly_pattern_average_excludes_still_in_flight_day fails RED before the fix (2.5 != 3.0) and passes GREEN after weekly_pattern.qmd adopts the same raw_absent/unsettled exclusion stats_coverage.qmd already uses; full pytest suite, ruff check/format, --check contract validation, and the web/vitest suite stay green."
status: "active"
---

# RunGoal
