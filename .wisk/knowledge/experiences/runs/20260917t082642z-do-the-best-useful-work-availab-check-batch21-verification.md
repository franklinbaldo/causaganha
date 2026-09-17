---
type: "RunCheck"
id: "run-checks/20260917t082642z-do-the-best-useful-work-availab/batch21-verification"
run: "runs/20260917T082642Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check; uv run ruff format --check; uv run pytest -q tests/segmenter_dataset; uv run python scripts/segmenter_governance_status.py; uv run python scripts/segmenter_semantic_audit.py"
result: "ruff check/format --check clean; pytest -q tests/segmenter_dataset: 391 passed, 0 failed (all dots, exit code 0); governance_status confirms document_count 161->167, annotation_count 214->220, val/test ceiling 24/24->25/25; semantic_audit flagged zero new findings among the 6 new documents (all 10 existing findings belong to pre-existing corpus documents, confirmed by doc_id)."
status: "pass"
evidence: "batch21-ingestion"
goal: "batch21-trf2"
---

# RunCheck
