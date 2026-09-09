---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-ko7vqq-evidence-red-test"
run_id: "2026-09-09-exciting-mccarthy-ko7vqq"
goal_id: "2026-09-09-exciting-mccarthy-ko7vqq-goal-datajud-enrich-erro-not-ok-on-parse-failure"
kind: "test_red"
reference: "tests/datajud/test_datajud_enrich.py::test_enrich_marks_a_malformed_document_as_erro_not_ok"
summary: "Ran `uv run pytest tests/datajud/test_datajud_enrich.py::test_enrich_marks_a_malformed_document_as_erro_not_ok -v` against the pre-fix service.py: FAILED with `AssertionError: assert 'ok' == 'erro'` at the `assert failed_entry.status == \"erro\"` line -- the malformed CNJ's manifest entry was stamped status='ok' by the unfixed enrich(), exactly the reported bug."
---

# Evidência: teste RED

`assert 'ok' == 'erro'` -- o CNJ com documento malformado foi marcado `status='ok'` pelo `enrich()` antes da correção, confirmando o bug relatado pela investigação.
