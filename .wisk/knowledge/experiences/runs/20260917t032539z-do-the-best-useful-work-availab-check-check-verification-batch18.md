---
type: "RunCheck"
id: "run-checks/20260917t032539z-do-the-best-useful-work-availab/check-verification-batch18"
run: "runs/20260917T032539Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check .; uv run ruff format --check .; uv run pytest -q tests/segmenter_dataset/; uv run pytest -q tests/knowledge/test_backlog.py; uv run pytest -q (full repo suite); scripts/segmenter_governance_status.py before/after; scripts/segmenter_semantic_audit.py; independent verbatim-fidelity re-verification of all 6 tagged docs against source"
result: "All green: ruff check/format clean; full repo pytest suite 100% pass (no failures, 1 skip, unrelated deprecation warning only); tests/segmenter_dataset/ green; tests/knowledge/test_backlog.py green after fixing last_verified_run_id to use the wisk: provenance prefix; scripts/segmenter_governance_status.py confirms document_count 143->149, val/test ceiling 21/21->22/22; segmenter_semantic_audit.py finds zero new findings on the 6 new documents (all 9 flagged findings pre-exist from earlier documents)."
status: "pass"
evidence: "run-evidence/20260917t032539z-do-the-best-useful-work-availab/evidence-batch18-ingested"
goal: "run-goals/20260917t032539z-do-the-best-useful-work-availab/goal-segmenter-batch18"
---

# RunCheck
