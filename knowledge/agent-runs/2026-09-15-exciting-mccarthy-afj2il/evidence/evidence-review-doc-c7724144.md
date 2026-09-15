---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-afj2il-evidence-review-doc-c7724144"
run_id: "2026-09-15-exciting-mccarthy-afj2il"
goal_id: "2026-09-15-exciting-mccarthy-afj2il-goal-scale-segmenter-reviews"
kind: "diff"
reference: "data/segmenter/reviews/doc_c772414481d672a6886be6f4f9d261c2/rev_5be5efc2b459c5ead839d4f26e5d11e9.xml"
summary: "Segunda ReviewRecord desta rodada: acórdão de Turma Recursal (recurso inominado, deserção por preparo intempestivo), adjudicada a partir de A (histórica, general-purpose, 13 labels) e B (nova, independente, subagente Técnica 1 modelo haiku, família prompt_subagents:haiku, 17 labels antes de drop_excluded_categories). Disagreements reais resolvidos: 3 fundamentacao_legal + 1 ref_normativa só em B (A tinha falso-negativo total apesar de listar a categoria em covered_categories) -- aceitos; dispositivo_abertura só em B, dentro do VOTO individual -- rejeitado, anti-padrão explícito da guideline para acórdão; resultado só em B também dentro do VOTO -- rejeitado, mantido o resultado de A (corretamente dentro de acordao_decisorio); ementa_fim com fronteiras diferentes (A inclui o numeral '2.' da última linha, B não) -- mantida a fronteira mais completa de A."
---

# Evidência: ReviewRecord doc_c772414481d672a6886be6f4f9d261c2

`store.write_review` aceitou sem levantar `NonIndependentReviewError` (A
`seeded_with=none`/`general-purpose`, B `seeded_with=none`/`haiku` --
famílias distintas, confirmado via `annotations_are_independent` antes da
ingestão). Verbatim fidelity e `validate_record` (`check_final_invariants`
+ checagem de pares) verificados programaticamente antes de cada chamada
de script, zero erros na resolução final.

**Artefato de qualidade encontrado e corrigido antes da ingestão:** a
reprodução bruta do subagente B omitiu a palavra isolada "ACÓRDÃO" (o
cabeçalho de seção entre EMENTA e o bloco `acordao_decisorio`) -- uma
falha de verbatim fidelity real (diferença de 8 caracteres,
`len("ACÓRDÃO ")`), detectada rodando `_text_element_to_labels` contra o
texto-fonte armazenado antes de qualquer chamada a
`annotate_second_independent.py`. Corrigida manualmente reinserindo o
texto ausente (fora de qualquer tag, igual ao tratamento de A) antes da
ingestão -- mesmo padrão de "verificar antes de confiar" já praticado em
rodadas anteriores para artefatos de OOXML corrompido.
