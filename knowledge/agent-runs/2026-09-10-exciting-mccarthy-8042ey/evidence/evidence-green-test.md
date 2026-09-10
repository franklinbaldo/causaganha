---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-8042ey-evidence-green-test"
run_id: "2026-09-10-exciting-mccarthy-8042ey"
goal_id: "2026-09-10-exciting-mccarthy-8042ey-goal-writeback-constants-drift"
kind: "test_green"
reference: "tests/test_render_manifest_writeback.py"
summary: "Command: uv run pytest tests/test_render_manifest_writeback.py -q. All tests pass after rewriting write_back_csv's djen_raw ibis.cases() branch to reference ABSENT/BARE_200_RAW/PREFIXED_200_RAW_PREFIX/NO_PUBLICATIONS_SENTINEL (already imported at module top from djen_backup.absent_consistency) instead of the hardcoded 'absent'/'200'/'200:'/'no_publications' literals. The new test_write_back_derives_from_absent_consistency_constants_not_retyped_literals passes: the TJSP row (patched-matching djen_status/djen_raw) is now rewritten to the patched sentinel, and the TJRO row (matching only the original literals, not the patched constants) is correctly left untouched. The pre-existing test_write_back_makes_absent_200_rows_self_consistent and test_apply_deltas_is_set_based_and_keeps_uploaded_never_absent both stayed green unmodified, since the constants' real-world string values are unchanged by the fix."
---

# Evidência GREEN

Após a correção, os dois testes do arquivo passam: o teste pré-existente de auto-consistência absent/200 (valores reais inalterados) e o novo teste de derivação-de-constantes (via monkeypatch).
