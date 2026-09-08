---
type: "RunEvidence"
id: "run-evidence/20260908t112621z-do-the-best-useful-work-availab/evidence-red-test"
run: "runs/20260908T112621Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_render_manifest_compaction.py::test_normalize_manifest_downgrades_absent_with_empty_raw_to_unknown"
summary: "Background Explore-agent audit found scripts/render_manifest_parquet.py's _normalize_manifest only rewrites the absent+bare-200 contradiction, missing the sibling 'absent with empty djen_raw -> downgrade to unknown' rule that src/djen_backup/manifest.py's _normalize_event (line 744) already enforces per CLAUDE.md's explicit instruction. Added a RED test asserting the downgrade; confirmed it fails against current code (AssertionError: assert 'absent' is None) via 'uv run pytest tests/test_render_manifest_compaction.py -q'."
goal: "goal-continue-work"
---

# RunEvidence
