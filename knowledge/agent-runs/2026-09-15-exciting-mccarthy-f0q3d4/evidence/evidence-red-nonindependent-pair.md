---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-f0q3d4-evidence-red-nonindependent-pair"
run_id: "2026-09-15-exciting-mccarthy-f0q3d4"
goal_id: "2026-09-15-exciting-mccarthy-f0q3d4-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "scripts/adjudicate_segmenter_review.py ; src/segmenter_dataset/store.py::_require_independent_inputs"
summary: "RED real: scripts/adjudicate_segmenter_review.py levantou NonIndependentReviewError para doc_b8a4a405e45ffe9a1ab11cf902f849e2 e doc_ec1f5133660dc174fe80e615f3f46dd2. Causa raiz: minha seleção inicial de candidatos filtrou só por 'exatamente 1 anotação', sem checar annotator_config.seeded_with -- as duas anotações históricas existentes eram 'historical_migration:round_e'/model_assisted_correction_v1 com seeded_with='model_draft_checkpoint_inference' (seeded, não elegível como metade de um par independente), não 'none'. Corrigido filtrando o pool para seeded_with=='none' (13 candidatos reais em vez de 27 aparentes) e trocando os 2 documentos-alvo."
---

# Evidência: RED real do guard de independência, e correção da seleção de candidatos

Comando:

```
uv run python scripts/adjudicate_segmenter_review.py --data-root data/segmenter \
  --document-id doc_b8a4a405e45ffe9a1ab11cf902f849e2 \
  --annotation-a ann_651453d557935b640907bc6e7805212c \
  --annotation-b ann_e35191bd895f59a0fa47df63d56a904e \
  ...
```

Saída:

```
segmenter_dataset.store.NonIndependentReviewError: review '...' is 'accepted'
but its input_annotation_ids don't resolve to an independent pair (RFC 0012
§9): needs >= 2 resolvable annotations, unseeded and from distinct model
families; found 2 resolvable
```

Diagnóstico ao vivo (`segmenter_dataset.mechanical.annotations_are_independent`):
a anotação histórica `ann_651453d557935b640907bc6e7805212c` tinha
`annotator_config.seeded_with = "model_draft_checkpoint_inference"`, não
`"none"` — falha `is_independent_capable()`. Minha consulta inicial ao pool
de candidatos (`store.list_documents/list_annotations/list_reviews`) filtrava
só "exatamente uma anotação, nenhuma review", sem checar `seeded_with` da
anotação existente — 27 documentos aparentavam ser candidatos válidos, mas
só 13 realmente eram (o resto tinha a única anotação existente já seeded,
tornando qualquer segunda anotação não-pareável para review independente).

Correção: recomputei o pool com o filtro correto
(`anns[0].annotator_config.seeded_with == 'none'`) e escolhi dois novos
documentos-alvo do pool real (`doc_c502b14fd24cd8133897a1863d25e30a`,
`doc_4d89a2699daf927cca28e543ebfd3efc`, ambos com anotação existente
`llm_technique1:batch1`/`prompt_subagents:general-purpose`, já unseeded).
As duas anotações extras já gravadas para
`doc_b8a4a405e45ffe9a1ab11cf902f849e2`/`doc_ec1f5133660dc174fe80e615f3f46dd2`
(`ann_e35191bd895f59a0fa47df63d56a904e`,
`ann_abf77b0e311b106b752703ef63f37dbd`) permanecem no store — são
`AnnotationRecord`s mecanicamente válidos (verbatim-fidelity e RFC 0012 §11
confirmados) e contam para `train_eligible_document_ids`; só não formam par
independente com a anotação seeded já existente, então esses dois documentos
seguem sem review nesta rodada. Nenhuma reversão feita — o store é
append-only por design (RFC 0012 §3.1, `annotation_id` é hash de conteúdo).
