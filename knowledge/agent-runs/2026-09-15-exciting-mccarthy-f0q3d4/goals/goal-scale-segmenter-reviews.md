---
type: AgentGoal
id: "2026-09-15-exciting-mccarthy-f0q3d4-goal-scale-segmenter-reviews"
run_id: "2026-09-15-exciting-mccarthy-f0q3d4"
goal: "Produzir mais um incremento real de ReviewRecords adjudicados para #1051/RFC 0012, sobre o pool atualizado de 27 documentos com exatamente uma anotação unseeded e nenhuma review (review_count=27 no início deste incremento)."
rationale: "RFC 0012 Sec 5.4 exige >=30 val + >=30 test ReviewRecords adjudicados antes do release v8 do segmentador; a issue #1051 pede uma escala inicial de 30-50 documentos. #1469/#1468 (Parquet/CNJ) estão esgotados no que não depende das credenciais IA ausentes (#1472 bloqueada desde 11/09); #1482 (CORS archive.org) já foi investigado e confirmado sem solução viável sem infraestrutura fora de escopo. #1051 segue sendo a única frente de domínio real, desbloqueada e não esgotada nesta janela -- o mesmo mecanismo já provado por 9+ rodadas consecutivas (PRs #1505-#1529, 11->27)."
success_signal: "uv run python scripts/segmenter_governance_status.py mostra review_count e evaluation_eligible_count subindo de 27 para >=29 ao final da rodada, com pelo menos 2 novos ReviewRecords reais persistidos em data/segmenter/reviews/, cada um resolvendo uma disagreement real entre a anotação histórica existente e uma segunda anotação genuinamente independente (subagente Técnica 1 isolado, sem ver a anotação existente, família distinta da já registrada para o documento), ingerida via scripts/annotate_second_independent.py com verbatim-fidelity confirmada programaticamente. store.write_review aceita ambas sem levantar NonIndependentReviewError. uv run pytest tests/segmenter_dataset -q e ruff check/format ficam verdes."
status: "in_progress"
---

# Goal: escalar ReviewRecords do segmentador (rodada f0q3d4)

Dois documentos-alvo escolhidos entre os 27 candidatos remanescentes com
exatamente uma anotação unseeded e nenhuma review (calculado via
`SegmenterDatasetStore.list_documents/list_annotations/list_reviews`).
Prioriza os menores documentos do pool, como as rodadas anteriores, para
manter o esforço de leitura/anotação do subagente tratável em um único
turno.
