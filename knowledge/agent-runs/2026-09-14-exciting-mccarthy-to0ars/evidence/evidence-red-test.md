---
type: AgentEvidence
id: "2026-09-14-exciting-mccarthy-to0ars-evidence-red-test"
run_id: "2026-09-14-exciting-mccarthy-to0ars"
goal_id: "2026-09-14-exciting-mccarthy-to0ars-goal-verify-values-bucket"
kind: "test_red"
reference: "tests/test_audit_cnj_parquets.py::TestResolveVerifyValues, ::TestReadValueOrder"
summary: "Added TestResolveVerifyValues (3 tests covering pass-through of every non-VERIFY_VALUES classification, sorted->VERIFIED_SORTED, inversion->VERIFIED_UNSORTED, unreadable->stays VERIFY_VALUES) and TestReadValueOrder (3 tests: a real single-row-group Parquet fixture with values already sorted in physical file order, one with a genuine adjacent-row inversion, and a missing file). Ran `uv run pytest tests/test_audit_cnj_parquets.py -q`: collection fails immediately with `ImportError: cannot import name 'VERIFIED_SORTED' from 'scripts.audit_cnj_parquets'` -- confirms RED (the new constants/functions do not exist yet in the pre-change script)."
---

# RED: testes para verificação real de valores no bucket verify_values

`uv run pytest tests/test_audit_cnj_parquets.py -q` falha na coleta com `ImportError: cannot import name 'VERIFIED_SORTED'` -- confirma que os novos testes (6 casos, cobrindo `resolve_verify_values` e `read_value_order`) estão vermelhos contra o script ainda não alterado.
