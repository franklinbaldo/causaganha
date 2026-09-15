---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-7drjlg-evidence-review-doc-254a2148"
run_id: "2026-09-15-exciting-mccarthy-7drjlg"
goal_id: "2026-09-15-exciting-mccarthy-7drjlg-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "data/segmenter/reviews/doc_254a21481f0881a28220cd162f7e0c6a/rev_6cea7b99d8d63bab3080b55fdafbff93.xml"
summary: "Oitavo ReviewRecord real da store (review_count 7->8), o mais denso em disagreements desta rodada: 4 spans só em A, 7 só em B antes da adjudicação. A anotação histórica (A, model_family=historical_migration_unspecified) omitiu por completo relatorio_inicio e a citação de waiver do art. 38 (fundamentacao_legal) -- padrão que corresponde EXATAMENTE ao exemplo canônico da própria guideline (linha 35: 'A decision citing art. 38 to waive the relatorio and art. 55 for custas/honorarios has two spans'; linha 47: cláusula de waiver é fundamentacao_legal, não relatorio_fim). A também fundiu indevidamente 'Sem custas ou honorários' em um único span custas_inicio -- custas e honorarios são categorias distintas na ontologia (guideline linhas 50-51) -- e rotulou 'artigo 55, da Lei 9.099/95.' como custas_fim quando é uma citação legal (fundamentacao_legal). B (ann_6986a3d0894ba392716b628d0f6658f5, model_family=prompt_subagents:general-purpose) corrigiu todos os quatro pontos. Esta revisão, por sua vez, corrigiu dois pontos sobre a própria B antes de aceitar como resolução: (1) dispositivo_abertura tinha a vírgula final dentro do span ('...examinado,'), inconsistente com o precedente já aceito nesta mesma rodada (doc_3dd38e93: 'Ante ao exposto' sem vírgula) -- vírgula movida para fora; (2) a anotação continha um span ref_normativa ('Lei 9.099/95, art. 53, § 4º') -- categoria explicitamente fora do espaço treinável da ontologia v8 (RFC 0012 §5 decisão 1: pré-passe regex na inferência) -- removida do resolution-file (annotate_second_independent.py já a descarta automaticamente das anotações persistidas, mas o script de adjudicação não replica esse descarte no resolution-file, então foi feito manualmente nesta revisão -- achado de processo registrado como AgentDecision desta rodada)."
---

# Review real #8: doc_254a21481f0881a28220cd162f7e0c6a

`uv run python scripts/segmenter_governance_status.py` antes deste review: review_count=7. Após: review_count=8, evaluation_eligible_count=8.
