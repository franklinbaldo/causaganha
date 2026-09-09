---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-ko7vqq-evidence-green-test"
run_id: "2026-09-09-exciting-mccarthy-ko7vqq"
goal_id: "2026-09-09-exciting-mccarthy-ko7vqq-goal-datajud-enrich-erro-not-ok-on-parse-failure"
kind: "test"
reference: "tests/datajud/test_datajud_enrich.py::test_enrich_marks_a_malformed_document_as_erro_not_ok"
summary: "After the fix (fetch_capas returns (capas, failed_cnjs); enrich() marks any pending CNJ in failed_cnjs-and-not-found as STATUS_ERRO), `uv run pytest tests/datajud/ -v` -> 75 passed (up from 74 pre-existing + this 1 new test). The full tests/datajud/ module (archive, client, dedup, enrich, manifest, models, state) stays green, including tests/datajud/test_datajud_state.py's fetch_capas stub, updated to the new tuple return signature."
---

# Evidência: teste GREEN

Após a correção, os 75 testes de `tests/datajud/` passam, incluindo o novo teste e o stub de `fetch_capas` em `test_datajud_state.py`, atualizado para a nova assinatura de retorno (tupla).
