---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-my6ovw-check-semantic-audit-batch26"
run_id: "2026-09-24-exciting-mccarthy-my6ovw"
goal_id: "2026-09-24-exciting-mccarthy-my6ovw-goal-djen-sample-batch26"
command: "uv run python scripts/segmenter_semantic_audit.py --store data/segmenter"
result: "passed"
evidence_id: "2026-09-24-exciting-mccarthy-my6ovw-evidence-batch26-ingested"
summary: "9 findings reported, all on pre-existing documents from prior batches (doc_12f989ac.., doc_2a07306d.., doc_3b0be436.., doc_3cffd796.., doc_b0c36490.., doc_b8a4a405.., doc_c5021b4f.., doc_c7724144.., doc_d61aecbf.., doc_db852d2a.., doc_f985597a..) -- the 7 '_collapsed' findings among them are exactly tests/segmenter_dataset/test_segmenter_audit_scripts.py's existing allowlist set, unchanged. Neither new document (doc_6363b6b0.., doc_d3de3dfe..) appears in any finding."
---

# Check: auditoria semântica pós-lote-26
