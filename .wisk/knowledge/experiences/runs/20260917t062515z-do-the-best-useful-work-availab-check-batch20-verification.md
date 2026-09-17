---
type: "RunCheck"
id: "run-checks/20260917t062515z-do-the-best-useful-work-availab/batch20-verification"
run: "runs/20260917T062515Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check; uv run ruff format --check; uv run pytest -q tests/segmenter_dataset"
result: "ruff check/format clean. pytest -q tests/segmenter_dataset: 391 passed, 0 failed (full suite green) after fixing tests/segmenter_dataset/test_segmenter_audit_scripts.py's collapsed-false-positive allowlist to include the new TRF2/301222762 document (reviewed and confirmed a false positive, same documented shape as 5 pre-existing entries). scripts/segmenter_governance_status.py confirms document_count=161, val/test ceiling 24/24. PR #1581 opened and pushed twice (d125791 ingestion, 561962a test fix)."
status: "pass"
evidence: "batch20-ingestion"
goal: "batch20-trf2"
---

# RunCheck
