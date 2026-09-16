---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-96cgqx-evidence-batch13-green-ingested"
run_id: "2026-09-16-exciting-mccarthy-96cgqx"
goal_id: "2026-09-16-exciting-mccarthy-96cgqx-goal-djen-sample-batch13"
kind: "test_green"
reference: "scripts/ingest_djen_sample_technique1_batch.py; scripts/segmenter_governance_status.py; tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch13_corpus_growth"
summary: "GREEN: scripts/ingest_djen_sample_technique1_batch.py ingeriu 2 documentos (doc_787698602321e64112c51ea16be1ad5e=TJSE, doc_cfa06dbce6009c921f4f66a5126c2056=TJRS) apos declarar docs/planning/evidence/segmenter-djen-sample-batch13-overrides.json para o par pendente custas+honorarios (mesmo padrao ja documentado da classe de risco 1, verificado contra o texto-fonte bruto de cada documento antes de declarar). scripts/segmenter_governance_status.py confirma document_count 121->123 ao vivo. O teste de regressao test_real_store_reflects_batch13_corpus_growth agora passa. git status --short data/segmenter mostrou exatamente 2 pares documento/anotacao novos (sem colisao de concorrencia). Contagem direta de ord= nas anotacoes: 19 ancoras reais (TJSE) e 8 (TJRS), nao o defeito de anotacao vazia da classe de risco 10. uv run python scripts/segmenter_semantic_audit.py --store data/segmenter encontrou 9 achados, nenhum nos dois documentos novos (todos pre-existentes e ja na allowlist). uv run pytest tests/segmenter_dataset -q: 390 testes, verde."
---

# Evidencia: GREEN lote 13

## Ingestao

```
Ingested 2 document(s):
  doc_cfa06dbce6009c921f4f66a5126c2056
  doc_787698602321e64112c51ea16be1ad5e
```

## Verificacao contra o store real

`git status --short data/segmenter`:
```
?? data/segmenter/annotations/doc_787698602321e64112c51ea16be1ad5e/
?? data/segmenter/annotations/doc_cfa06dbce6009c921f4f66a5126c2056/
?? data/segmenter/documents/doc_787698602321e64112c51ea16be1ad5e.xml
?? data/segmenter/documents/doc_cfa06dbce6009c921f4f66a5126c2056.xml
```

Contagem de ancoras reais (`grep -o 'ord="[0-9]*"' ann_*.xml | wc -l`):
TJSE=19, TJRS=8 -- confirma anotacao real, nao vazia.

## Governanca

```
"document_count": 123,
"annotation_count": 176,
"review_count": 31,
...
"val_ceiling_at_full_adjudication": 18,
"test_ceiling_at_full_adjudication": 18,
"meets_rfc_0012_split_floor": false,
"corpus_scale_blocks_floor": true
```

## Audit semantico

9 achados, todos em documentos ja existentes antes deste lote (nenhum em
doc_787698602321e64112c51ea16be1ad5e ou doc_cfa06dbce6009c921f4f66a5126c2056).

## Teste de regressao

`uv run pytest tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch13_corpus_growth -q` -- PASSED (1 passed).

`uv run pytest tests/segmenter_dataset -q` -- 390 testes, verde (exit code 0).
