---
type: "RunEvidence"
id: "run-evidence/20260908t172434z-do-the-best-useful-work-availab/evidence-red-test"
run: "runs/20260908T172434Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_backfill_probe_classify.py::test_probe_one_reports_no_publications_for_200_sem_comunicacoes"
summary: "RED: added a respx-mocked test asserting _probe_one's live_raw=='no_publications' for an HTTP 200 body {'status':'Sem comunicações'}; ran against the pre-fix implementation and it failed with AssertionError: assert '200' == 'no_publications', proving the classification bug live rather than by inspection alone."
goal: "run-goals/20260908t172434z-do-the-best-useful-work-availab/goal-fix-backfill-probe-classification"
---

# RunEvidence
