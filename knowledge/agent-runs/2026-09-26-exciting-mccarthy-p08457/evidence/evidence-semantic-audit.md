---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-p08457-evidence-semantic-audit"
run_id: "2026-09-26-exciting-mccarthy-p08457"
goal_id: "2026-09-26-exciting-mccarthy-p08457-goal-1051-test-split-adjudication"
kind: "other"
reference: "uv run python scripts/segmenter_semantic_audit.py"
summary: "Rodado apos a ingestao dos 2 ReviewRecords. Os 7 achados HIGH ('_collapsed') reportados sao exatamente os mesmos doc_ids ja na allowlist de tests/segmenter_dataset/test_segmenter_audit_scripts.py (pre-existentes, nao relacionados a esta rodada). Nenhum dos 2 documentos desta rodada (doc_0db5fffa04141a164fb9c48f11bb8c01, doc_174797b9bfde68303b3e00c43ac291fe) aparece em qualquer achado."
---

# Evidencia: semantic audit sem achados novos

`scripts/segmenter_semantic_audit.py` apos a ingestao: os 7 achados
`_collapsed` reportados sao os mesmos ja allowlisted por rodadas
anteriores; nenhum toca os 2 documentos desta rodada.
