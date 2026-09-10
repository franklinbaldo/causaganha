---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-8042ey-evidence-red-test"
run_id: "2026-09-10-exciting-mccarthy-8042ey"
goal_id: "2026-09-10-exciting-mccarthy-8042ey-goal-writeback-constants-drift"
kind: "test_red"
reference: "tests/test_render_manifest_writeback.py::test_write_back_derives_from_absent_consistency_constants_not_retyped_literals"
summary: "Command: uv run pytest tests/test_render_manifest_writeback.py -q, run against write_back_csv before the fix (hardcoded 'absent'/'200'/'200:'/'no_publications' literals). Failed with: AssertionError: assert 'zzz-200' == 'zzz-sentinel' at tests/test_render_manifest_writeback.py:196 -- the TJSP row (djen_status patched to 'zzz-absent', djen_raw patched-matching 'zzz-200') was NOT rewritten to the patched sentinel 'zzz-sentinel', because write_back_csv's own hardcoded literal check for djen_status == 'absent' (the real word, not the patched name) never matched 'zzz-absent'. This directly demonstrates write_back_csv was not deriving its behavior from the imported djen_backup.absent_consistency constants, confirming the drift risk described in this round's goal."
---

# Evidência RED

`write_back_csv` reescreve os mesmos literais do contrato `absent`/`200` em vez de referenciar as constantes já importadas de `djen_backup.absent_consistency`. O teste que monkeypatcha essas constantes falha contra o código original porque a função nunca as consulta.
