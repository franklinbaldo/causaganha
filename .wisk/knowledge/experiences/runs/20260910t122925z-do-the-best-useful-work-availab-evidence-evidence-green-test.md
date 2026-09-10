---
type: "RunEvidence"
id: "run-evidence/20260910t122925z-do-the-best-useful-work-availab/evidence-green-test"
run: "runs/20260910T122925Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_generate_homepage_widgets.py::test_build_widgets_finds_last_closed_month_data_across_year_boundary"
summary: "GREEN after fixing scripts/generate_homepage_widgets.py: build_widgets/_activity_summary now take an injectable now: datetime, and build_widgets discovers a com_urls_window/adv_urls_window (year plus year-1) used by activity_summary and top_tribunais_30d, while top_advogados_atividade stays scoped to the single requested year. All 4 tests in the file pass."
goal: "goal-january-boundary-widgets"
---

# RunEvidence
