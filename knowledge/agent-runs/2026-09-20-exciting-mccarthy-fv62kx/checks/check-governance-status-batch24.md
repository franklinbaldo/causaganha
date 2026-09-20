---
type: AgentCheck
id: "2026-09-20-exciting-mccarthy-fv62kx-check-governance-status-batch24"
run_id: "2026-09-20-exciting-mccarthy-fv62kx"
command: "uv run python scripts/segmenter_governance_status.py, rodado ao vivo antes e depois da ingestao do lote."
result: "passed"
evidence_id: "2026-09-20-exciting-mccarthy-fv62kx-evidence-codex-fixes-batch24"
summary: "Antes: document_count=179, val_ceiling=test_ceiling=27. Apos ingestao inicial (6 docs): document_count=185, val_ceiling=test_ceiling=28. Apos a correcao pos-Codex (TJBA revertido por near-duplicate, lote liquido 5 docs): document_count=184, annotation_count=237, val_ceiling=test_ceiling=28 (reconfirmado ao vivo). Ainda abaixo do piso RFC 0012 Sec 5 item 4 (>=30/>=30)."
---

# Check: governance status antes/depois (batch24)

Antes (início da rodada):

```
document_count: 179, annotation_count: 232, val_ceiling: 27, test_ceiling: 27
```

Depois (pós-ingestão):

```
document_count: 185, annotation_count: 238, review_count: 31,
val_count: 28, test_count: 3, val_ceiling: 28, test_ceiling: 28,
meets_rfc_0012_split_floor: false, corpus_scale_blocks_floor: true
```
