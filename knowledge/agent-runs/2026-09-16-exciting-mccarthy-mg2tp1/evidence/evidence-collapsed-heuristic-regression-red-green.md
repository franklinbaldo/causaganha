---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-mg2tp1-evidence-collapsed-heuristic-regression-red-green"
run_id: "2026-09-16-exciting-mccarthy-mg2tp1"
goal_id: "2026-09-16-exciting-mccarthy-mg2tp1-goal-djen-sample-batch4"
kind: "test"
reference: "tests/segmenter_dataset/test_segmenter_audit_scripts.py::test_real_store_has_at_most_the_one_known_collapsed_false_positive"
summary: "RED: after ingesting batch4, uv run pytest tests/segmenter_dataset -q failed this exact regression guard -- doc_f985597a64cc7b5ad06731c072915a7a (TRF4, id 574643532) newly appeared in the audit's fundamentacao_legal_collapsed findings, which the test asserts is an exact-membership set. Investigated live: the document's stored annotation has exactly 1 fundamentacao_legal span ('conforme art. 447 do CC') while its raw text has 4 total 'art.' occurrences -- the other 3 (CPC art. 886, CPC art. 903, CC art. 182) were correctly tagged ref_normativa by the annotating subagent but silently dropped from the stored annotation by _drop_excluded_categories (ref_normativa is excluded from the trainable label space per ontology.EXCLUDED_CATEGORIES), leaving the heuristic's raw-text 'art.' count to see 4 against only 1 stored tag and flag a false collapse. This is the identical false-positive shape the test already documents for doc_3cffd7961e9fc910f6ae628f5aaa6c40 (RFC 0012 Sec 9 scale-up, 2026-09-15) -- not a new omission, confirmed by checking that all 3 dropped 'art.' mentions match exactly the 3 ref_normativa citations the subagent reported tagging, with no fourth unaccounted-for mention. GREEN: extended the test's allowlist (assertion set + docstring) to include doc_f985597a64cc7b5ad06731c072915a7a with the same documented reasoning, per the test's own stated policy ('extend this allowlist with a documented reason, never silence the assertion'). uv run pytest tests/segmenter_dataset -q now passes in full (373 tests, 0 failures)."
---

# Evidencia: regressao RED->GREEN no audit de fundamentacao_legal_collapsed

Ingerir o lote 4 introduziu um novo falso-positivo no heuristico de
`fundamentacao_legal_collapsed` do audit semantico, capturado pelo
proprio teste de regressao existente
(`test_real_store_has_at_most_the_one_known_collapsed_false_positive`).
Investigacao ao vivo confirmou que e a mesma forma de falso-positivo ja
documentada para outro documento: 3 mencoes de "art." corretamente
marcadas como `ref_normativa` (categoria excluida do espaco de rotulos
treinavel) sao descartadas da anotacao armazenada, mas o heuristico conta
"art." no texto bruto, nao nas tags armazenadas. Corrigido estendendo a
allowlist do proprio teste (nao silenciando a asserção), com o mesmo
padrao de documentacao ja usado para o caso anterior. Suite completa de
`tests/segmenter_dataset` volta a passar (373 testes, 0 falhas).
