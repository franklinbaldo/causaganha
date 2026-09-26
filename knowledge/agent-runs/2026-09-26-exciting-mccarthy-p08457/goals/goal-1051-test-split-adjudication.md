---
type: AgentGoal
id: "2026-09-26-exciting-mccarthy-p08457-goal-1051-test-split-adjudication"
run_id: "2026-09-26-exciting-mccarthy-p08457"
goal: "Adjudicar 2 documentos do segmenter (doc_0db5fffa04141a164fb9c48f11bb8c01/TRF6 e doc_174797b9bfde68303b3e00c43ac291fe/TRF2, ambos acordao de embargos de declaracao) em ReviewRecords aceitos, via segunda anotacao genuinamente independente (model_family distinto), para avancar test_count de 2 para >=4 rumo ao piso RFC 0012 Sec 5 item 4 (>=30 val, >=30 test), agora que o teto de escala de corpus (#1050) parou de bloquear (30/30 desde a rodada ku8qje)."
rationale: "`scripts/segmenter_governance_status.py`, executado ao vivo no inicio desta rodada, confirma document_count=197/review_count=32/val_count=30 (no teto)/test_count=2 (muito atras do teto de 30) -- o gargalo real agora e puramente cobertura de adjudicacao do lado TEST, nao mais escala de corpus. Uma simulacao ao vivo (assign_splits com cada candidato elegivel -- anotacao unica, seeded_with=='none', sem review -- adicionado isoladamente a evaluation_eligible, antes de gastar qualquer esforco de anotacao) mostrou que 134 dos 141 candidatos disponiveis aumentariam test_count se adjudicados; os dois documentos mais curtos desse conjunto (2604 e 3468 caracteres) foram escolhidos por tratabilidade dentro do orcamento desta rodada, e confirmados por simulacao conjunta (nao so isolada) a aumentarem test_count de 2 para 4 quando adjudicados juntos."
success_signal: "2 novos ReviewRecords aceitos ingeridos em data/segmenter/reviews/ via scripts/adjudicate_segmenter_review.py, cada um resolvendo uma segunda anotacao independente (model_family=prompt_subagents:haiku, seeded_with=none) contra a anotacao original (model_family=prompt_subagents:general-purpose); ambas as segundas anotacoes verificadas por reconstrucao verbatim mecanica (_text_element_to_labels) e mechanical.validate_record ANTES da ingestao; scripts/segmenter_governance_status.py mostrando review_count>=34 e test_count>=4 apos a ingestao; uv run pytest -q tests/segmenter_dataset verde; uv run ruff check/format --check limpos; okf-parser check conformant; mudancas commitadas, pushed, PR aberta."
status: "achieved"
---

# Goal: adjudicar 2 documentos para avancar o test_count de #1051

O teto de corpus (RFC 0012 Sec 5 item 4) ja atingiu 30/30 (rodada
ku8qje). O gargalo real agora e cobertura de adjudicacao do lado TEST
(test_count=2 de 30). Este goal adjudica 2 documentos curtos
(TRF6/TRF2, acordaos de embargos de declaracao) via segunda anotacao
genuinamente independente, escolhidos por simulacao previa confirmando
que aumentam test_count.
