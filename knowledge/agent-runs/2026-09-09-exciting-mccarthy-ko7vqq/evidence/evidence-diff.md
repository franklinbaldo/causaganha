---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-ko7vqq-evidence-diff"
run_id: "2026-09-09-exciting-mccarthy-ko7vqq"
goal_id: "2026-09-09-exciting-mccarthy-ko7vqq-goal-datajud-enrich-erro-not-ok-on-parse-failure"
kind: "diff"
reference: "src/datajud/service.py, tests/datajud/test_datajud_enrich.py, tests/datajud/test_datajud_state.py"
summary: "165-line diff across 3 files. src/datajud/service.py: fetch_capas() now returns (list[ProcessoCapa], set[str]) instead of just list[ProcessoCapa] -- the second element is the set of normalized CNJs whose hit failed pydantic validation but still carried a readable numeroProcesso; enrich() unpacks the tuple and marks any pending CNJ present in failed_cnjs-and-absent-from-found as STATUS_ERRO instead of STATUS_OK. tests/datajud/test_datajud_enrich.py: new test_enrich_marks_a_malformed_document_as_erro_not_ok plus a CNJ_B constant. tests/datajud/test_datajud_state.py: its fetch_capas monkeypatch stub updated to the new (capas, empty_set) return shape so test_datajud_state.py's own 4 tests keep passing unmodified in behavior."
---

# Evidência: diff

Mudança contida em 3 arquivos: `fetch_capas` passa a retornar também o conjunto de CNJs cuja falha de validação pôde ser atribuída; `enrich()` usa esse conjunto para marcar `STATUS_ERRO` em vez de `STATUS_OK`. Teste novo mais ajuste do stub existente que dependia da assinatura antiga.
