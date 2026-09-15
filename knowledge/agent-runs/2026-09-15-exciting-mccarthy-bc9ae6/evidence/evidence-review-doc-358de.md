---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-bc9ae6-evidence-review-doc-358de"
run_id: "2026-09-15-exciting-mccarthy-bc9ae6"
goal_id: "2026-09-15-exciting-mccarthy-bc9ae6-goal-scale-segmenter-reviews"
kind: "diff"
reference: "data/segmenter/reviews/doc_358de4e83426bf9b9d0b9e5f8c8e16e2/rev_bf237258f3eaccda546515208885ece2.xml"
summary: "ReviewRecord real adjudicando doc_358de4e83426bf9b9d0b9e5f8c8e16e2 (sentença TJRO, litigância de má-fé) entre a anotação histórica (ann_225f15a6..., família prompt_subagents:general-purpose, batch1) e a nova segunda anotação independente (ann_e5b124aa..., família prompt_subagents:haiku, seeded_with=none)."
---

# Evidência: adjudicação de doc_358de4e83426bf9b9d0b9e5f8c8e16e2

Disagreements resolvidos:

- `fundamentacao_legal`: a nova anotação encontrou 3 citações legítimas adicionais que a histórica perdeu -- "estampado no art. 14 do CPC" (dentro da citação doutrinária de Nery), "Lei nº 8.906/94" e "Em seu art. 32" (Estatuto dos Advogados, citado diretamente pelo juízo). Guideline v7 linha 25/35: "tag every distinct citation, not just the first". Adotadas as 3 no resultado final, totalizando 6 spans `fundamentacao_legal` (histórica tinha 3).
- `resultado`: o rascunho bruto da nova anotação tagueava as duas cláusulas "CONDENO" (multa + honorários), violando a regra de no-máximo-um-span (guideline Regra 3) -- `MechanicalValidationError` rejeitou o rascunho antes mesmo de poder ser persistido como `AnnotationRecord` (ver decision-resultado-single-anchor-fix). Corrigido para manter só a primeira ("CONDENO a parte requerente solidariamente com o seu patrono em multa"), coincidindo com a escolha independente já feita pela anotação histórica para este mesmo span.
- Demais categorias (`cabecalho`, `ref_processual`, `dispositivo_abertura`, `valor_condenacao`, `encerramento`): concordância exata de span entre as duas anotações -- sem disagreement a resolver.

Independência verificada: `store.write_review` aceitou sem `NonIndependentReviewError` (famílias `prompt_subagents:general-purpose` vs `prompt_subagents:haiku`, ambas `seeded_with="none"`).
