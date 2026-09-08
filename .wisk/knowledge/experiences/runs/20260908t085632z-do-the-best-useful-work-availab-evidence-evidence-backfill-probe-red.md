---
type: "RunEvidence"
id: "run-evidence/20260908t085632z-do-the-best-useful-work-availab/evidence-backfill-probe-red"
run: "runs/20260908T085632Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "uv run pytest tests/test_backfill_probe_classify.py -v"
summary: "RED confirmed: test_classify_treats_no_publications_as_absent fails with 'other:no_publications' == 'absent' -- scripts/backfill_probe.py::_classify hardcodes {'404','400'} for absent instead of using the canonical ABSENT_CODES set, so it never learned about the no_publications sentinel. Other 5 cases pass, isolating the RED to this one gap."
goal: "run-goals/20260908t085632z-do-the-best-useful-work-availab/goal-fix-backfill-probe-classify"
---

# RunEvidence
