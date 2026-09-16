---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-la7bsl-evidence-no-new-semantic-findings"
run_id: "2026-09-16-exciting-mccarthy-la7bsl"
kind: "validation_result"
reference: "uv run python scripts/segmenter_semantic_audit.py (live run, post-ingestion)"
summary: "Ran the semantic audit after ingesting batch 5. It reports 7 HIGH findings, all against pre-existing document ids from earlier batches/migrations; none reference any of this batch's 7 new document ids (053d49b451c676060bfa8bcd8e601a34, 3f6fbeed801469206bd017a34cec4d15, bbf8d42e93289ef4c2368bb207793096, 372fbafbf83b374da59608c69eb2a3ce, c41321b105269252919a5d4d730800a2, 246d157bf2c416ed78340710b74ed1cb, 35f2734cfbf51c80667f5fc689a45ae0). This batch introduces no new category-collapse or long-anchor anomaly."
---

# Evidencia: nenhum novo achado no audit semantico

`scripts/segmenter_semantic_audit.py` rodado apos a ingestao do lote 5
continua reportando os mesmos 7 achados pre-existentes de lotes
anteriores -- nenhum aponta para os 7 novos document_ids deste lote.
