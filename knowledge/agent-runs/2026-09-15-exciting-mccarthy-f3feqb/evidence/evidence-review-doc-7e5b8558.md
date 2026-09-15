---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-f3feqb-evidence-review-doc-7e5b8558"
run_id: "2026-09-15-exciting-mccarthy-f3feqb"
goal_id: "2026-09-15-exciting-mccarthy-f3feqb-goal-scale-segmenter-reviews"
kind: "diff"
reference: "data/segmenter/reviews/doc_7e5b8558463338f1f74ee7ba8924ccfa/rev_d8444591df04d09b68e044504eef4ae5.xml"
summary: "Primeira ReviewRecord desta rodada: sentença de Juizado Especial (homologação de acordo), adjudicada a partir de A (histórica, general-purpose, 7 labels) e B (nova, independente, subagente Técnica 1 modelo haiku, família prompt_subagents:haiku, 8 labels). 3 disagreements reais resolvidos: cabecalho_inicio (A mais estreito, adotado), resultado (B mais completo, adotado), fundamentacao_legal+ref_normativa x2 (só em B, A tinha falso-negativo total), encerramento_inicio/fim (só em A, B tinha falso-negativo total do bloco de assinatura)."
---

# Evidência: ReviewRecord doc_7e5b8558463338f1f74ee7ba8924ccfa

`store.write_review` aceitou sem levantar `NonIndependentReviewError`
(A `seeded_with=none`/`general-purpose`, B `seeded_with=none`/`haiku` --
famílias distintas, confirmado via `annotations_are_independent` antes da
ingestão). Verbatim fidelity e `check_final_invariants`/`validate_pairs`
verificados programaticamente antes da chamada ao script (ver
scratchpad), zero erros. Resolução completa registrada no próprio XML da
review (`<resolution>`), citando cada disagreement real via comparação de
spans, não uma preferência mecânica.
