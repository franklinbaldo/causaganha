---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-2cjjig-evidence-review-doc-69b98539"
run_id: "2026-09-15-exciting-mccarthy-2cjjig"
goal_id: "2026-09-15-exciting-mccarthy-2cjjig-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "data/segmenter/reviews/doc_69b98539c565dcf153a6bc9a7117b69d/rev_a9e3585f6c686485b5b9dab5e9418c5d.xml"
summary: "13º ReviewRecord real da store (review_count 12->13). Subagente Técnica 1 isolado (sem visibilidade da anotação histórica) produziu ann_80187700285353ec109411836ee74a8e (model_family=prompt_subagents:general-purpose, seeded_with=none -- par independente com a anotação histórica ann_094b62dd530d3ad08f078de0d74221fd, model_family=prompt_subagents:haiku, seeded_with=none; annotations_are_independent confirmado True). Mesma família de disagreement de doc_613907cc (mesmo formato de export capa+ementa-estruturada do TJRO, adjudicado na mesma rodada): (1) cabecalho, (2) fundamentacao_legal ('nos termos dos arts. 884 e 934 do CC', item III), (3) ref_processual (span sem 'AUTOS N.'), (4) ementa_inicio (literal 'EMENTA') -- histórico não tinha os quatro spans/tinha spans mais largos; adotado o do subagente em todos. (5) ementa_fim -- nem o histórico (fechava no último texto do documento) nem o subagente integralmente (fechava cedo, antes de 'I. CASO EM EXAME'); resolvido não-casado por consistência com doc_613907cc, mesma rodada (ver decision-ementa-extends-to-eod-consistency). (6) resultado -- histórico marcou o bloco operativo DECISÃO ('RECURSO NÃO PROVIDO'), subagente marcou a paráfrase posterior no item 7 ('Recurso desprovido.'); adotado o span do histórico, por consistência com doc_613907cc onde as duas anotações já concordavam nesse mesmo bloco (ver decision-resultado-operative-decisao-block). valor_condenacao coincidiu exatamente ('R$ 29.188,58') e foi mantido sem alteração."
---

# Review real #13: doc_69b98539c565dcf153a6bc9a7117b69d

`uv run python scripts/segmenter_governance_status.py` antes desta review: review_count=12. Depois: review_count=13.
