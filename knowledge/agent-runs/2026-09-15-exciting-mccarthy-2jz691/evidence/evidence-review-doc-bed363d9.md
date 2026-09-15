---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-2jz691-evidence-review-doc-bed363d9"
run_id: "2026-09-15-exciting-mccarthy-2jz691"
goal_id: "2026-09-15-exciting-mccarthy-2jz691-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "data/segmenter/reviews/doc_bed363d93062300e16c05c0627d9ac01/rev_2f30e75629c74f95fff2e160d0867fb2.xml"
summary: "Décimo primeiro ReviewRecord real da store (review_count 10->11), o mais denso em disagreements desta rodada. Subagente Técnica 1 isolado produziu ann_c3bf7c3de024c900367597d7d583aee8 (independente da histórica). Disagreements: (1) relatorio_inicio -- histórico usou 'Vistos.' (convenção já observada no restante do corpus), subagente usou 'Versam os autos sobre' (também defensável, mas inconsistente com o padrão já estabelecido); adotado o histórico. (2) capitulo_merito -- subagente OMITIU a região inteira apesar do cue claro 'Fundamento e decido.' (falso negativo); reincorporada do histórico, preservando as 2 fundamentacao_legal aninhadas que o subagente identificou dentro dela. (3) fundamentacao_legal -- subagente encontrou 5 citações distintas vs. 1 do histórico; adotado o conjunto completo do subagente. (4) honorarios -- subagente fundiu indevidamente inicio+fim num único span 'Sem condenação em honorários em razão do desfecho consensual da demanda' (MESMO anti-padrão de fusão já registrado por 7drjlg em doc_254a2148); revertido para o par matched do histórico (inicio 'Sem condenação em honorários' / fim 'em razão do desfecho consensual da demanda.'). (5) custas -- mantido unmatched como o subagente decidiu: o único candidato a fim do histórico ('Código de Processo Civil.') sobrepõe caracteres com a citação fundamentacao_legal do subagente ('na forma do art. 90, § 2º, do Código de Processo Civil') -- manter ambos violaria a Rule 5 (sem spans sobrepostos); preferida a citação legal (mandato explícito de tag every distinct citation) sobre o fim de custas, que a guideline permite deixar unmatched (allowed_unmatched declarado com o motivo). (6) 1 span ref_normativa do subagente removido manualmente (mesmo gap corrigido estruturalmente nesta rodada). cabecalho, ref_processual, dispositivo_abertura ('ANTE O EXPOSTO', formula literal -- as duas anotações concordaram aqui), resultado e encerramento coincidiram e foram mantidos."
---

# Review real #11: doc_bed363d93062300e16c05c0627d9ac01

`uv run python scripts/segmenter_governance_status.py` antes: review_count=10. Depois: review_count=11, evaluation_eligible_count=11 -- acima da meta mínima do success_signal (>=10).
