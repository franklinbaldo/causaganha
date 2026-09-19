---
type: AgentDecision
id: "2026-09-19-exciting-mccarthy-gbf44b-decision-extend-collapsed-allowlist"
run_id: "2026-09-19-exciting-mccarthy-gbf44b"
question: "tests/segmenter_dataset/test_segmenter_audit_scripts.py::test_real_store_has_at_most_the_one_known_collapsed_false_positive failed after ingesting batch22: the semantic audit flagged a new fundamentacao_legal_collapsed finding on doc_12f989ac213c5eadf857aacc69b33ad2 (TJTO/285747298) that the test's hardcoded allowlist doesn't yet include. Is this a real annotation omission that needs repair, or a known false-positive shape that should extend the allowlist?"
choice: "Extended the test's allowlist (both the docstring's per-document triage prose and the assertion's set literal) with a documented reason for doc_12f989ac213c5eadf857aacc69b33ad2, after manually verifying against the raw source text that every extra 'art.' occurrence sits inside an already-covered quoted precedent/statute block, not this document's own uncovered reasoning."
rationale: "The test's own docstring is explicit: 'If this test starts seeing more than these six findings, a new real omission was introduced and needs the same triage -- repair it, or extend this allowlist with a documented reason, never silence the assertion.' I did the triage first, not last: read the raw texto_limpo around every 'art.' occurrence the audit heuristic counted, and confirmed all of them are (a) inside a verbatim-quoted STJ precedent ementa already covered by one ref_normativa tag on the precedent citation itself, or (b) inside a verbatim-quoted statute transcription already covered by fundamentacao_legal+ref_normativa on the introductory sentence -- the exact same shape (heuristic double-counts substring 'art.' inside a block a single wider tag already covers) as all six pre-existing allowlist entries, several of which cite the identical 'ref_normativa citations inside a bibliography/ementa block' pattern. This is not a case of silencing the assertion (the set literal is still exact, still fails on any *other* new finding) -- it is exactly the documented escape hatch the test itself prescribes, applied only after genuine verification against source text, matching the same discipline every prior batch's semantic-audit review applied (never assume a recorded status/heuristic-flag is right without checking live)."
---

# Decisao: estender o allowlist de falsos positivos collapsed

O teste de regressao em `test_segmenter_audit_scripts.py` mantem um
`assert collapsed_doc_ids == {...}` com um conjunto fixo de 6
`doc_id`s ja triados como falsos positivos conhecidos do heuristico
`fundamentacao_legal_collapsed`/`valor_condenacao_collapsed`. O lote 22
introduziu um setimo documento (TJTO/285747298,
`doc_12f989ac213c5eadf857aacc69b33ad2`) que o audit tambem sinaliza.

Antes de estender o allowlist, li o `texto_limpo` bruto ao redor de
cada ocorrencia de "art." que o heuristico contou (7 no total, 1 real
`fundamentacao_legal` ja tageado) e confirmei que as 6 ocorrencias
extras pertencem a um bloco de ementa de precedente do STJ citado
verbatim (ja coberto por uma tag `ref_normativa` sobre a propria
citacao REsp) e a uma transcricao literal do texto legal (ja coberta
por `fundamentacao_legal`+`ref_normativa` na frase introdutoria) --
exatamente a mesma classe ja documentada para os 6 casos existentes no
allowlist (nenhuma dessas ocorrencias e linguagem de
raciocinio-com-conector adicional que devesse gerar uma nova tag).

Estendi tanto a prosa do docstring (com a mesma estrutura de triagem
documentada por caso) quanto o literal do assert, seguindo a instrucao
explicita do proprio teste: "extend this allowlist with a documented
reason, never silence the assertion". O teste continua sendo um guard
de regressao exato -- qualquer OUTRO doc_id novo ainda falha o teste e
exige a mesma triagem.
