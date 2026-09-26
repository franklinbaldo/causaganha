---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-ku8qje-check-green-test-and-governance"
run_id: "2026-09-26-exciting-mccarthy-ku8qje"
goal_id: "2026-09-26-exciting-mccarthy-ku8qje-goal-segmenter-batch28"
command: "uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch28_corpus_growth (após a ingestão); uv run python scripts/segmenter_governance_status.py --store data/segmenter"
result: "passed"
evidence_id: "2026-09-26-exciting-mccarthy-ku8qje-evidence-batch28-ingested"
summary: "Teste RED->GREEN confirmado. `segmenter_governance_status.py`: document_count=197, annotation_count=255, review_count=32, val_count=30, test_count=2, val_ceiling_at_full_adjudication=30, test_ceiling_at_full_adjudication=30, meets_rfc_0012_split_floor=false, corpus_scale_blocks_floor=false (marco: primeira vez que o teto real cruza o piso RFC 0012 Sec 5 item 4)."
---

# Check: teste GREEN + governance status pós-ingestão
