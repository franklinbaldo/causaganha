---
goal: "Fix scripts/generate_homepage_widgets.py: activity_summary (last closed month) and top_tribunais_30d (rolling 30 days) silently go empty during the first weeks of every January because build_widgets() discovers comunicacoes/advogados catalog URLs only for the single --year CLI arg (current calendar year), while both widgets need data that can fall in the previous year's djen-{tribunal}-{year} catalog item near the boundary."
id: "run-goals/20260910t122925z-do-the-best-useful-work-availab/goal-january-boundary-widgets"
kind: "task-advance"
rationale: "Flagged as a not-yet-fixed follow-on by the immediately preceding round's RunOutcome (run-outcomes/20260910t114603z-.../outcome-final), which fixed a sibling NULL-date/ia_item filter bug in the same file (PR #1419) and explicitly named this January edge case as worth fixing proactively. Verified by reading _activity_summary (needs period_year=year-1 when now.month==1) and _top_tribunais_30d (needs current_date - 30 days, which crosses into the prior year for roughly the first 30 days of each year) against build_widgets' single-year URL discovery -- both widgets go empty exactly when real prior-year data exists but isn't discovered."
run: "runs/20260910T122925Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "tests/test_generate_homepage_widgets.py has a new RED-then-GREEN test that builds a local manifest+comunicacoes+advogados parquet fixture with only a djen-tjro-2026 catalog item, calls build_widgets(year=2027, now=<a January 2027 timestamp>), and asserts activity_summary is non-empty with periodo='2026-12' -- failing on unmodified code (empty com_urls for year=2027) and passing after widening discovery to include year-1 for the rolling-window widgets. Full pytest suite, ruff check, and ruff format --check stay green; top_advogados_atividade's discovery stays scoped to the single year (unaffected, by design)."
type: "RunGoal"
---

# RunGoal
