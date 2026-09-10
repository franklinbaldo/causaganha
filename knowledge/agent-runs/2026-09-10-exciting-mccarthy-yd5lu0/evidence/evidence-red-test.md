---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-yd5lu0-evidence-red-test"
run_id: "2026-09-10-exciting-mccarthy-yd5lu0"
goal_id: "2026-09-10-exciting-mccarthy-yd5lu0-goal-download-zip-cancels-siblings"
kind: "test_red"
reference: "uv run pytest tests/djen_backup/test_download_zip_segment_cancellation.py -q, run against unmodified src/djen_backup/djen.py (git stash on the djen.py fix only, new test file present)"
summary: "New test fails as expected on unfixed djen.py: cancelled_starts=set() AND completed_starts=set() -- the three sibling segment Tasks are neither cancelled nor completed, proving they are genuinely orphaned (hung forever on an Event that only a cancellation could resolve), not merely racing a timer."
---

# Evidência RED

```
FAILED tests/djen_backup/test_download_zip_segment_cancellation.py::test_download_zip_cancels_sibling_segments_on_failure
AssertionError: sibling segment downloads were not cancelled after download_zip raised -- cancelled=set() completed=set()
assert set() == {5000000, 10000000, 15000000}
```

Comando: `uv run pytest tests/djen_backup/test_download_zip_segment_cancellation.py -q` contra `src/djen_backup/djen.py` sem a correção (fixture `_fast_sleep` de `tests/djen_backup/conftest.py` descartada da equação ao usar `asyncio.Event().wait()` em vez de `asyncio.sleep()` no fake -- garante que a única forma do teste terminar é via cancelamento real, não corrida de tempo).
