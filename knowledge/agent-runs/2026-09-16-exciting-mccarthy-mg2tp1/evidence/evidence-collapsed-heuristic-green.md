---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-mg2tp1-evidence-collapsed-heuristic-green"
run_id: "2026-09-16-exciting-mccarthy-mg2tp1"
goal_id: "2026-09-16-exciting-mccarthy-mg2tp1-goal-djen-sample-batch4"
kind: "test_green"
reference: "tests/segmenter_dataset/test_segmenter_audit_scripts.py::test_real_store_has_at_most_the_one_known_collapsed_false_positive"
summary: "GREEN: extended the test's allowlist (assertion set + docstring) to include doc_f985597a64cc7b5ad06731c072915a7a with the same documented false-positive reasoning already used for the prior precedent document, per the test's own stated policy ('extend this allowlist with a documented reason, never silence the assertion'). uv run pytest tests/segmenter_dataset -q now passes in full (373 tests, 0 failures), and uv run pytest -q for the whole repo passes with 0 failures outside the expected, scaffold-documented completeness gate on this round's own in-progress run.md."
---

# Evidencia: GREEN no audit de fundamentacao_legal_collapsed

Corrigido estendendo a allowlist do proprio teste (nao silenciando a
asserção), com o mesmo padrao de documentacao ja usado para o caso
anterior (`doc_3cffd7961e9fc910f6ae628f5aaa6c40`). Suite completa de
`tests/segmenter_dataset` volta a passar (373 testes, 0 falhas); suite
completa do repositorio passa, exceto o gate de completude do proprio
`run.md` desta rodada, ainda em preenchimento.
