---
type: AgentEvidence
id: "2026-09-17-exciting-mccarthy-0hjgmk-evidence-batch17-ingested"
run_id: "2026-09-17-exciting-mccarthy-0hjgmk"
goal_id: "2026-09-17-exciting-mccarthy-0hjgmk-goal-djen-sample-batch17"
kind: "diff"
reference: "git status --short data/segmenter; docs/planning/evidence/segmenter-djen-sample-batch17-*.json; scripts/segmenter_governance_status.py"
summary: "5 documentos reais (TJBA/574460085, TJMA/42736393, TJMA/42730832, TJCE/363647616, TJCE/363657243) ingeridos no store via scripts/ingest_djen_sample_technique1_batch.py. document_count 138->143, annotation_count 191->196 (confirmado ao vivo). git status --short data/segmenter confirma exatamente 5 novos documents/*.xml e 5 novos annotations/<id>/, sem write no-op silencioso."
---

# Evidencia: lote 17 ingerido

Um sexto candidato (TJBA/574460088) foi descartado ANTES da anotacao
por ser near-duplicate do template de TJBA/574460085
(`difflib.SequenceMatcher.ratio()=0.98` no texto-fonte bruto, mesmo
juizo/juiz/tipo de decisao).

Fluxo RED->GREEN observado na propria ingestao (nao um teste automatizado,
mas o mesmo padrao de contrato usado pelo script de ingestao):

- RED: primeira tentativa de ingestao sem overrides falhou com 3
  documentos rejeitados por `mechanical validation failed` (pares
  unmatched sem razao declarada: `relatorio` em TJCE/363647616;
  `capitulo_merito`/`custas`/`honorarios` em TJMA/42730832; `custas` em
  TJMA/42736393), apenas 2/5 ingeridos.
- GREEN: apos declarar `--allowed-unmatched-overrides` com razao
  verificada contra o texto-fonte bruto para cada par, os 5/5
  documentos foram ingeridos com sucesso, tanto no dry-run store quanto
  no store real `data/segmenter`.

`scripts/segmenter_governance_status.py` (ao vivo, apos ingestao real):
`document_count=143`, `annotation_count=196`, `val_ceiling=test_ceiling=21`
(inalterado -- lote train-only, sem segunda anotacao independente).

`uv run python -m scripts.segmenter_semantic_audit --store data/segmenter`
nao reportou nenhum achado novo para os 5 IDs de documento deste lote
(`doc_47841c1fefc19a845b7f344b93153f59`,
`doc_d3456d129a7e8e7fb01dd6e4de85cb0c`,
`doc_184545c85a6015ee00699c594da0d83b`,
`doc_d32142e637afdd0dc5f843a8717673e0`,
`doc_a4274c9897fd3907743cedaec6dd4e10`) -- todos os achados existentes
pertencem a documentos pre-existentes de lotes anteriores.
