---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-jyqinl-evidence-final-batch-ingested"
run_id: "2026-09-16-exciting-mccarthy-jyqinl"
goal_id: "2026-09-16-exciting-mccarthy-jyqinl-goal-djen-sample-batch2"
kind: "runtime"
reference: "docs/planning/evidence/segmenter-djen-sample-batch2-2026-09-16.json, docs/planning/evidence/segmenter-djen-sample-batch2-overrides.json, data/segmenter/documents/ (6 new *.xml files)"
summary: "Final ingestion of batch2: 6/8 selected real candidates ingested (TJPB, TJRN, TJRJ, TJMA, TJBA, TJRR -- 6 tribunals never before in the store), 2 dropped (TJTO, TJGO -- see decision-skip-html-entity-encoded-candidates). scripts/segmenter_governance_status.py before/after: document_count 68->74, train_eligible_count 68->74, val_ceiling_at_full_adjudication 10->11, test_ceiling_at_full_adjudication 10->11. store.list_documents() confirms source.tribunal now spans 13 distinct tribunals (TJRO:61, TJMT:1, TJCE:1, TJES:1, TRF3:1, TRF5:1, TJSE:1, TJPA:1, TJRN:1, TJRJ:1, TJBA:1, TJPB:1, TJRR:1) -- up from 8 at the start of this round. 3 of the 6 ingested documents (TJRJ, TJMA, TJRR) needed a manually reviewed --allowed-unmatched-overrides entry for a dangling capitulo_merito/custas/honorarios/relatorio pair with no closing cue in the source text (same class as batch1 and TJBA, all in docs/planning/evidence/segmenter-djen-sample-batch2-overrides.json). uv run ruff check/format and uv run pytest tests/segmenter_dataset -q stayed green throughout -- no code changes were needed, this batch exercised the existing, already-tested ingestion mechanism end to end."
---

# Evidencia: lote 2 final -- 6/8 documentos reais ingeridos

```
$ uv run python scripts/segmenter_governance_status.py
# antes
document_count=68 val_ceiling_at_full_adjudication=10 test_ceiling_at_full_adjudication=10
# depois (6 documentos ingeridos)
document_count=74 val_ceiling_at_full_adjudication=11 test_ceiling_at_full_adjudication=11
```

Tribunais novos no store: TJPB, TJRN, TJRJ, TJMA, TJBA, TJRR (nenhum
presente antes desta rodada). TJTO e TJGO descartados por um problema de
qualidade de dados genuino e novo (entidades HTML literais nao decodificadas
em `texto_limpo`), registrado como decisao separada.
