---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-f0q3d4-decision-correct-candidate-filter"
run_id: "2026-09-15-exciting-mccarthy-f0q3d4"
goal_id: "2026-09-15-exciting-mccarthy-f0q3d4-goal-scale-segmenter-reviews"
question: "adjudicate_segmenter_review.py rejeitou os dois primeiros documentos-alvo com NonIndependentReviewError porque a anotação histórica existente era seeded, não unseeded -- meu filtro inicial de candidatos (exatamente 1 anotação, nenhuma review) não checava isso. Continuar sobre os mesmos 2 documentos de algum outro jeito, ou trocar de alvo?"
choice: "Trocar de alvo: recomputar o pool filtrando por annotator_config.seeded_with=='none' na anotação existente (13 candidatos reais de 27 aparentes) e escolher os 2 menores desse pool corrigido (doc_c502b14fd24cd8133897a1863d25e30a, doc_4d89a2699daf927cca28e543ebfd3efc)."
rationale: "annotate_second_independent.py só escreve a NOVA anotação como unseeded -- não pode tornar a anotação HISTÓRICA já seeded independente retroativamente. Produzir uma segunda anotação para um documento cuja única anotação existente é seeded nunca formaria um par independente, então insistir nos mesmos 2 documentos seria repetir o mesmo RED sem chance de GREEN. O pool real tem 13 candidatos genuinamente pareáveis -- suficiente para o incremento desta rodada sem depender de nenhuma mudança de mecanismo."
---

# Decisão: corrigir o filtro de candidatos após o RED de independência

As duas anotações já gravadas para os documentos originais permanecem no
store (válidas, mecanicamente corretas, apenas não pareáveis nesta rodada).
Prossegui com os 2 documentos do pool corrigido, ambos com anotação
existente unseeded (`llm_technique1:batch1`/`prompt_subagents:general-purpose`),
usando `model: haiku` nos subagentes de Técnica 1 desta vez para garantir
uma família de modelo distinta (`prompt_subagents:haiku`) sem depender de
metadado arbitrário.
