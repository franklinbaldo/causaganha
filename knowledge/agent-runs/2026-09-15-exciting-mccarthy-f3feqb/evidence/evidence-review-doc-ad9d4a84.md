---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-f3feqb-evidence-review-doc-ad9d4a84"
run_id: "2026-09-15-exciting-mccarthy-f3feqb"
goal_id: "2026-09-15-exciting-mccarthy-f3feqb-goal-scale-segmenter-reviews"
kind: "diff"
reference: "data/segmenter/reviews/doc_ad9d4a846d91353b317e3017245ffee5/rev_ecf89103125edcd3402d7b39011dc1c0.xml"
summary: "Segunda ReviewRecord desta rodada: sentença de execução contra a Fazenda Pública (indeferimento da inicial), adjudicada a partir de A (histórica, general-purpose, 0 labels -- falha de zero-tag pré-existente na store) e B (nova, independente, subagente Técnica 1 modelo haiku, 12 labels). Adotado B integralmente com 1 correção: cabecalho_fim rejeitando âncora em lixo de extração OOXML ('X-NONE') a favor do último conteúdo substantivo real ('Advogado do(a) EXECUTADO:')."
---

# Evidência: ReviewRecord doc_ad9d4a846d91353b317e3017245ffee5

`store.write_review` aceitou sem levantar `NonIndependentReviewError` (A
`seeded_with=none`/`general-purpose`, B `seeded_with=none`/`haiku` --
famílias distintas). Este documento tinha uma anotação histórica com 0
labels (falha de zero-tag documentada como modo de falha conhecido em
`data/segmenter_splits/technique1_annotation_prompt.md`); a adjudicação
não foi bloqueada por isso porque a segunda anotação (B) é uma leitura
completa e independentemente verificada (verbatim fidelity + mechanical
validation, zero erros). Uma nota anexada à ReviewRecord registra o gap de
extração OOXML como item para uma futura auditoria de qualidade de
extração, sem bloquear esta adjudicação.
