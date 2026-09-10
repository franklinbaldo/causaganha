---
type: AgentCheck
id: "2026-09-10-exciting-mccarthy-yd5lu0-check-red-test"
run_id: "2026-09-10-exciting-mccarthy-yd5lu0"
goal_id: "2026-09-10-exciting-mccarthy-yd5lu0-goal-download-zip-cancels-siblings"
command: "uv run pytest tests/djen_backup/test_download_zip_segment_cancellation.py -q (against unmodified src/djen_backup/djen.py)"
result: "failed"
evidence_id: "2026-09-10-exciting-mccarthy-yd5lu0-evidence-red-test"
summary: "Expected failure before the fix: cancelled_starts=set(), completed_starts=set() -- the three sibling segment Tasks are genuinely orphaned (neither cancelled nor completed), confirming the test exercises the real bug rather than an already-passing assertion."
---

# Check: RED antes do fix

`uv run pytest tests/djen_backup/test_download_zip_segment_cancellation.py -q` falha contra `djen.py` sem a correção: os três `Tasks` irmãos ficam pendentes para sempre (nem cancelados, nem completos).
