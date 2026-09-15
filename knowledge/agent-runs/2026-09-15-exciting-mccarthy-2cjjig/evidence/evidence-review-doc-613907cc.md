---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-2cjjig-evidence-review-doc-613907cc"
run_id: "2026-09-15-exciting-mccarthy-2cjjig"
goal_id: "2026-09-15-exciting-mccarthy-2cjjig-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "data/segmenter/reviews/doc_613907ccb28de44b6bde08b443bb369f/rev_9ff2f9fce63e9667777e59e60ba24277.xml"
summary: "12º ReviewRecord real da store (review_count 11->12). Subagente Técnica 1 isolado (sem visibilidade da anotação histórica) produziu ann_3ad1422545f54018ed21b5b73fe84545 (model_family=prompt_subagents:general-purpose, seeded_with=none -- par independente com a anotação histórica ann_2c6dab90834331c28b7f1812785eeea8, model_family=prompt_subagents:haiku, seeded_with=none; annotations_are_independent confirmado True antes da adjudicação). Disagreement real: (1) cabecalho_inicio/fim + acordao_decisorio_inicio/fim -- o histórico não tinha NENHUM desses 4 spans (falso negativo completo); adotados do subagente ('PODER JUDICIÁRIO'..'DECISÃO:'..'POR MAIORIA'..'ALBUQUERQUE DA ROSA.'), ancoras genuínas do formato de export capa+ementa do TJRO. (2) fundamentacao_legal -- histórico não tinha; adotado o do subagente ('previstos na Resolução n. 1000/2021 da ANEEL', item III Razões de Decidir). (3) ref_processual -- histórico incluía o rótulo 'AUTOS N.' junto ao número (span mais longo); adotado o span do subagente (só o número), mais fiel à regra de âncoras curtas. (4) ementa_inicio -- histórico ancorava no primeiro conteúdo substantivo ('Direito do consumidor'); adotado o do subagente (literal 'EMENTA', o cue que a guideline pede). (5) ementa_fim -- mantido não-casado (estende até EOD, ver decision-ementa-extends-to-eod-consistency) em vez do span do histórico no último texto do documento. resultado coincidiu exatamente entre as duas anotações (RECURSO NÃO PROVIDO no bloco DECISÃO) e foi mantido sem alteração."
---

# Review real #12: doc_613907ccb28de44b6bde08b443bb369f

`uv run python scripts/segmenter_governance_status.py` antes desta review: review_count=11. Depois: review_count=12.
