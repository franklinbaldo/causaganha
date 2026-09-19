---
type: AgentCheck
id: "2026-09-19-exciting-mccarthy-gbf44b-check-governance-status-batch22"
run_id: "2026-09-19-exciting-mccarthy-gbf44b"
command: "uv run python scripts/segmenter_governance_status.py (run before and after ingestion)"
result: "passed"
evidence_id: "2026-09-19-exciting-mccarthy-gbf44b-evidence-batch22-ingested"
summary: "document_count 167->173, annotation_count 220->226, val_ceiling=test_ceiling 25/25->26/26. meets_rfc_0012_split_floor still false, corpus_scale_blocks_floor still true."
---

# Check: governance status antes/depois do lote 22

Rodado antes da selecao de candidatos (estado inicial confirmado:
167/220/25/25) e novamente apos a ingestao real (173/226/26/26). Numeros
usados para calibrar a selecao de candidatos (evitar colisao com
trabalho concorrente) e para confirmar o avanco real do lote.
