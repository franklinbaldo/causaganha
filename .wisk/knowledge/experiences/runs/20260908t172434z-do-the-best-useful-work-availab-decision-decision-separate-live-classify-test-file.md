---
type: "RunDecision"
id: "run-decisions/20260908t172434z-do-the-best-useful-work-availab/decision-separate-live-classify-test-file"
run: "runs/20260908T172434Z-do-the-best-useful-work-available-in-this-reposi"
question: "Where should the new RED test for _probe_one's live classification live?"
decision: "Wrote it as a new file, tests/test_backfill_probe_live_classify.py, rather than in tests/test_backfill_probe_classify.py."
rationale: "The Write tool's first attempt overwrote tests/test_backfill_probe_classify.py wholesale, silently deleting an existing, unrelated, still-valid test suite for backfill_probe.py's other function, _classify (the manifest-raw -> category mapper, already fixed and covered separately). Caught it via 'git diff' before committing, restored the original file with 'git checkout --', and placed the new _probe_one tests in their own file instead -- avoids re-deleting that coverage and keeps each file's docstring accurate to what it actually covers (one tests the pure _classify mapper, the other tests _probe_one's live HTTP classification). The RunEvidence recorded earlier this round (evidence-red-test, evidence-green-diff) named the pre-correction file path; the actual test content and RED->GREEN result are unchanged, only the filename."
goal: "run-goals/20260908t172434z-do-the-best-useful-work-availab/goal-fix-backfill-probe-classification"
---

# RunDecision
