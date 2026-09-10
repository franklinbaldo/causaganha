---
type: "RunEvidence"
id: "run-evidence/20260910t122925z-do-the-best-useful-work-availab/evidence-red-test"
run: "runs/20260910T122925Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_generate_homepage_widgets.py::test_build_widgets_finds_last_closed_month_data_across_year_boundary"
summary: "RED confirmed: TypeError: build_widgets() got an unexpected keyword argument 'now' -- build_widgets/​_activity_summary currently call datetime.now(UTC) internally and discover comunicacoes/advogados URLs only for the single requested year, with no injectable clock and no year-1 lookback. Full failure captured via 'uv run pytest tests/test_generate_homepage_widgets.py -q'."
goal: "goal-january-boundary-widgets"
---

# RunEvidence
