---
type: AgentGoal
id: "2026-09-26-exciting-mccarthy-kgxf50-goal-1051-test-split-adjudication"
run_id: "2026-09-26-exciting-mccarthy-kgxf50"
goal: "Adjudicate 3 more segmenter documents (doc_d3de3dfe95769791db33077c54bd3724/TJSC, doc_4a8e16820fb9c8fa1d808d717d9a34d7/TJMG, doc_3b0be436ba6753185997c37b2b6b9765/TJSE) into accepted ReviewRecords via genuinely independent second annotations (distinct model_family), advancing test_count from 4 toward the RFC 0012 Sec 5 item 4 floor (>=30 val, >=30 test) now that the corpus-scale ceiling (#1050) sits at 30/30 (since round ku8qje) and val_count is already at that ceiling."
rationale: "scripts/segmenter_governance_status.py, run live at round start, confirms document_count=197/annotation_count=257/review_count=34/val_count=30 (at ceiling)/test_count=4 (far behind the 30 floor). The bottleneck is purely TEST-side adjudication coverage. A live simulation (assign_splits with each of the 139 single-annotated/seeded_with==none/unreviewed candidates added in isolation to evaluation_eligible, before any annotation effort) showed 132 of them individually raise test_count. The three shortest (for tractability within this round's budget) were confirmed by a JOINT simulation to raise test_count from 4 to 7 when all three are adjudicated together (val_count stays at 30, its ceiling)."
success_signal: "3 new accepted ReviewRecords ingested into data/segmenter/reviews/ via scripts/adjudicate_segmenter_review.py, each resolving a genuinely independent second annotation (model_family=prompt_subagents:haiku, seeded_with=none) against the document's existing first annotation (model_family=prompt_subagents:general-purpose); each second annotation verified by mechanical verbatim-fidelity reconstruction and mechanical.validate_record BEFORE ingestion; scripts/segmenter_governance_status.py showing review_count>=37 and test_count>4 (its pre-round value) after ingestion; a RED test declaring the contract fails before ingestion and passes GREEN after; uv run pytest -q tests/segmenter_dataset green; uv run ruff check/format --check clean; okf-parser check conformant; changes committed, pushed, PR opened."
status: "in_progress"
---

# Goal: adjudicate 3 documents to advance #1051's test_count

The corpus-scale ceiling (RFC 0012 Sec 5 item 4) already reached 30/30
(round `ku8qje`). The real bottleneck now is TEST-side adjudication
coverage (`test_count=4` of 30). This goal adjudicates 3 short
documents (TJSC/TJMG/TJSE) via genuinely independent second
annotation, chosen by live simulation confirming they raise
`test_count`.
