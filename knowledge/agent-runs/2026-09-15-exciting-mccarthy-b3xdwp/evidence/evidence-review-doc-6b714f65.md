---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-b3xdwp-evidence-review-doc-6b714f65"
run_id: "2026-09-15-exciting-mccarthy-b3xdwp"
goal_id: "2026-09-15-exciting-mccarthy-b3xdwp-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "data/segmenter/reviews/doc_6b714f6515beb1d38ba465e57c60c669/rev_b076d7987d591827850fa0bf6c91dc97.xml"
summary: "14º ReviewRecord real da store (review_count 13->14). Subagente Técnica 1 isolado (general-purpose, sem visibilidade da anotação histórica) produziu ann_ecb690bc858d34f2cb0202c5225ace5d (model_family=prompt_subagents:general-purpose, seeded_with=none -- par independente confirmado True com a anotação histórica ann_be5f9a936a32a6b3ba661f3ae25fc260, model_family=prompt_subagents:haiku, seeded_with=none). Verbatim-fidelity verificada programaticamente (tags removidas == texto do documento) antes da ingestão. Diff exato: 9 spans concordantes, 5 só em A (capitulo_merito_inicio/fim, honorarios_inicio/fim, valor_condenacao), 1 só em B (encerramento_fim). Resolução: adotadas as âncoras curtas de B para cabecalho_inicio/fim, relatorio_inicio, dispositivo_abertura e encerramento_inicio (mais fiéis aos exemplos literais da guideline, ver decision-trim-numbered-heading-prefixes); adotado encerramento_fim de B (falso negativo real de A); mantidos capitulo_merito_inicio/fim (numeral romano removido), honorarios_inicio/fim e as 3 ocorrências de fundamentacao_legal de A (falso negativo total de B nesses 5); REJEITADO valor_condenacao de A por erro de categoria (ver decision-reject-valor-condenacao-mislabel) -- não incluído na resolução final, então o total de spans na review (13) é menor que a soma de A (14) e B (12) sem sobreposição simples."
---

# Review real #14: doc_6b714f6515beb1d38ba465e57c60c669

`uv run python scripts/segmenter_governance_status.py` antes desta review: review_count=13. Depois: review_count=14.
