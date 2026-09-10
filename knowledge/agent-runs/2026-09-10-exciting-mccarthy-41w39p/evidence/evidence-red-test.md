---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-41w39p-evidence-red-test"
run_id: "2026-09-10-exciting-mccarthy-41w39p"
goal_id: "2026-09-10-exciting-mccarthy-41w39p-goal-background-upload-not-orphaned"
kind: "test_red"
reference: "uv run pytest -q tests/djen_backup/test_background_manifest_upload.py, run with the tracking/await lines reverted from engine.py (IA_UPLOAD_INTERVAL_SECONDS constant kept so the test exercises real behavior, not a missing-attribute error)"
summary: "FAILED with AssertionError at the `assert pipeline_task in pending` line: pipeline_task had already finished (result=None) while the mocked background manifest-segment upload was still blocked mid-flight on an unresolved asyncio.Event -- proving run_pipeline returns without ever waiting for its own background upload task on unmodified engine.py."
---

# Evidência RED

Comando: `uv run pytest -q tests/djen_backup/test_background_manifest_upload.py` contra `engine.py` com o rastreamento revertido (apenas as duas linhas de `background_tasks.add`/`add_done_callback` e o `if background_tasks: await asyncio.gather(...)` do `finally` removidas; a constante `IA_UPLOAD_INTERVAL_SECONDS` mantida).

```
E       AssertionError: run_pipeline returned while its own background manifest-segment upload was still in flight -- the periodic-upload safety net (CLAUDE.md: 'protects against crashes') can be silently abandoned instead of completing before shutdown
E       assert <Task finished name='Task-2' coro=<run_pipeline() done, defined at /home/user/causaganha/src/djen_backup/engine.py:356> result=None> in set()
```

`pipeline_task` já estava `done()` (com `result=None`) no momento em que `upload_started` foi sinalizado pela task de background ainda bloqueada em `release_upload.wait()` -- confirma que o `run_pipeline` não legislativo aguarda a task de upload em segundo plano antes de retornar.
