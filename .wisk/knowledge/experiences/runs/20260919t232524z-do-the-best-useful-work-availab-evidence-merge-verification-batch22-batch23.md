---
type: "RunEvidence"
id: "run-evidence/20260919t232524z-do-the-best-useful-work-availab/merge-verification-batch22-batch23"
run: "runs/20260919T232524Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "uv run ruff check / uv run ruff format --check / uv run okf-parser check knowledge --relational-schema okf.schema.sql / uv run pytest -q tests/segmenter_dataset -k batch23 / uv run pytest -q tests/segmenter_dataset (full suite) / uv run python scripts/segmenter_governance_status.py, all run against /tmp/wt-1586 (PR #1586's branch merged with origin/main after PR #1585 merged)"
summary: "PR #1585 (batch22) and PR #1586 (batch23) merged: #1585 squashed directly (e54a0b0); #1586 needed origin/main merged into its branch to resolve a single-field YAML conflict in knowledge/backlog/issue-1050.md (blocking_reason/unblock_condition prose), resolved by concatenating both batches' narratives in order and correcting batch23's deltas to the real post-batch22 baseline. After the merge commit (5ad9c7c): ruff check clean, ruff format --check clean (454 files), okf-parser check conformant (0 diagnostics, 2014 concepts), pytest -k batch23 pass, full pytest tests/segmenter_dataset 100% pass (238+ tests), live segmenter_governance_status.py confirmed document_count=179, annotation_count=232, val_ceiling=test_ceiling=27 -- exactly matching the hand-computed merge arithmetic (173+6, 226+6, 26+1)."
---

# RunEvidence
