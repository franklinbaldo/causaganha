---
type: "RunEvidence"
id: "run-evidence/20260915t052720z-do-the-best-useful-work-availab/evidence-audit-cnj-details"
run: "runs/20260915T052720Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "scripts/audit_cnj_parquets.py (CnjColumnDetails, _aggregate_cnj_column_details, _read_cnj_column_details, regeneration_plan_for) + tests/test_audit_cnj_parquets.py (TestAggregateCnjColumnDetails, TestRegenerationPlanFor, and extended TestReadFooterStats cases)"
summary: "RED confirmed first: new tests imported _aggregate_cnj_column_details/regeneration_plan_for before they existed -> ImportError on pytest collection. Implemented CnjColumnDetails (column_type/compression_codecs/encodings/total_compressed_size/total_uncompressed_size/has_bloom_filter) wired into FooterStats+read_footer_stats+_audit_file's report dict, and regeneration_plan_for(classification) mapping every bucket to an actionable plan string, also wired into the report. GREEN: uv run pytest tests/test_audit_cnj_parquets.py -q -> 44 passed. ruff check/format clean. Closes issue #1470's two remaining non-IA-gated acceptance criteria (Bloom filter/encoding/compression/size inspection detail; per-file regeneration plan)."
goal: "goal-task-advance"
---

# RunEvidence
