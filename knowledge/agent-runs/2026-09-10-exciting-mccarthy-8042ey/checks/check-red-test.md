---
type: AgentCheck
id: "2026-09-10-exciting-mccarthy-8042ey-check-red-test"
run_id: "2026-09-10-exciting-mccarthy-8042ey"
goal_id: "2026-09-10-exciting-mccarthy-8042ey-goal-writeback-constants-drift"
command: "uv run pytest tests/test_render_manifest_writeback.py -q (against write_back_csv before the constants fix, with the new monkeypatch-based test already added)"
result: "failed"
evidence_id: "2026-09-10-exciting-mccarthy-8042ey-evidence-red-test"
summary: "1 failed, 2 passed. test_write_back_derives_from_absent_consistency_constants_not_retyped_literals failed with AssertionError: assert 'zzz-200' == 'zzz-sentinel' -- confirming write_back_csv ignored the patched constants and used its own hardcoded literals."
---

# Check RED

Confirma que o teste novo falha contra o código original, provando a duplicação de literais.
