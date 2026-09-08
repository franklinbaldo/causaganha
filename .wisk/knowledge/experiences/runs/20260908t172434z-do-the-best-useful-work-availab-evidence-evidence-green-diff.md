---
type: "RunEvidence"
id: "run-evidence/20260908t172434z-do-the-best-useful-work-availab/evidence-green-diff"
run: "runs/20260908T172434Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "scripts/backfill_probe.py"
summary: "GREEN: rewrote _probe_one to classify live_raw via get_caderno_url (the canonical DJEN entry point every other caller in this codebase uses) plus segments.absent_raw_code for the DJENNotFoundError case, instead of reading the bare HTTP status code. All 3 tests in tests/test_backfill_probe_classify.py now pass (200-with-url -> '200', 200-Sem-comunicacoes -> 'no_publications', 403 -> '403'), diff: scripts/backfill_probe.py +46/-14 lines."
goal: "run-goals/20260908t172434z-do-the-best-useful-work-availab/goal-fix-backfill-probe-classification"
---

# RunEvidence
