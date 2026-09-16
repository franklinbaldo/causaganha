---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-zrek2s-evidence-batch7-ingested"
run_id: "2026-09-16-exciting-mccarthy-zrek2s"
kind: "runtime"
reference: "docs/planning/evidence/segmenter-djen-sample-batch7-2026-09-16.json, docs/planning/evidence/segmenter-djen-sample-batch7-overrides.json"
summary: "6 documentos reais (TJRJ, TJGO, TJTO, TJPB, TJMA, TJRR) anotados por 6 subagentes independentes via prompt canonico Technique 1 e ingeridos com sucesso em data/segmenter via scripts/ingest_djen_sample_technique1_batch.py. scripts/segmenter_governance_status.py confirma document_count 96->102, annotation_count 145->154, val_ceiling/test_ceiling 14->15."
---

# Evidencia: lote 7 ingerido

Comando de ingestao final (apos aplicar html.unescape/limpador HTML nos
candidatos TJGO/TJTO e corrigir o bug de strip() -- ver
`evidence-nbsp-strip-bug-fixed`):

```
uv run python -m scripts.ingest_djen_sample_technique1_batch \
  --candidates <candidates.json> \
  --tagged-dir <tagged/> \
  --output data/segmenter \
  --completed-at <timestamp> \
  --allowed-unmatched-overrides docs/planning/evidence/segmenter-djen-sample-batch7-overrides.json

Ingested 6 document(s):
  doc_e2216433d03144060baed62d47431434
  doc_f3e10e0e079dd38a0cb3bb6a6b9b4fc5
  doc_db7db0690740b39b106b2d2d4ad7a42d
  doc_bcbf5100e4683a75aa5b9a4f2158783e
  doc_2a07306d88d1acebcdc0aff9958f7009
  doc_22198f2efbe5ac2d85eb451af873d0f1
```

`scripts/segmenter_governance_status.py` antes/depois:

```
before: document_count=96, annotation_count=145, val_ceiling=14, test_ceiling=14
after:  document_count=102, annotation_count=154, val_ceiling=15, test_ceiling=15
```

25 tribunais permanecem representados (nenhum tribunal novo neste lote,
por escolha deliberada -- ver `goal-djen-sample-batch7`), mas cada um dos
6 tribunais escolhidos (TJRJ, TJGO, TJTO, TJPB, TJMA, TJRR) foi de 1 para
2 documentos no store, e a categoria `preliminar` ganhou instancias
novas (TJGO, TJMA, TJTO, TJRR tagged pares preliminar_inicio/fim).
