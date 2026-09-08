---
type: "RunEvidence"
id: "run-evidence/20260908t202452z-do-the-best-useful-work-availab/evidence-datasets-consultados-red"
run: "runs/20260908T202452Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/causaganha/decisoes/test_search.py::test_cnj_lookup_matches_juris_and_skips_stj_with_explicit_limitation and ::test_orgao_filter_matches_juris_and_skips_stj_with_explicit_limitation, new assertion added before the fix"
summary: "RED: both tests failed with \"assert 2 == 1\" -- search_decisions returned datasets_consultados=plan.total_datasets (2, includes STJ) even though the loop explicitly skips (continue) past STJ whenever skip_stj_for_orgao/skip_stj_for_cnj is true, so STJ is never actually queried."
decision: "run-decisions/20260908t202452z-do-the-best-useful-work-availab/decision-datajud-decisoes-clean-fix-scope"
---

# RunEvidence
