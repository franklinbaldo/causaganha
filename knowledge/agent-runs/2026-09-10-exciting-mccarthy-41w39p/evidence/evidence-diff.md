---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-41w39p-evidence-diff"
run_id: "2026-09-10-exciting-mccarthy-41w39p"
goal_id: "2026-09-10-exciting-mccarthy-41w39p-goal-background-upload-not-orphaned"
kind: "diff"
reference: "git diff src/djen_backup/engine.py (this session's working tree) + new file tests/djen_backup/test_background_manifest_upload.py"
summary: "Promoted the 600s IA-upload interval to a module constant (IA_UPLOAD_INTERVAL_SECONDS) so it is monkeypatchable in tests. run_pipeline now tracks every background manifest-upload Task in a set (add + add_done_callback to auto-discard on completion) and awaits the set in its existing finally block before returning. New test file tests/djen_backup/test_background_manifest_upload.py (1 test) proves the pipeline waits for a pending background upload instead of returning while it is still in flight."
---

# Evidência diff

```diff
diff --git a/src/djen_backup/engine.py b/src/djen_backup/engine.py
index 676fc4b..ca792b6 100644
--- a/src/djen_backup/engine.py
+++ b/src/djen_backup/engine.py
@@ -52,6 +52,8 @@ STAGING_DIR = Path("data/staging")
 MAX_STAGED_FILES = 15
 DJEN_SAFE_CONCURRENCY_FILE = Path("data/djen-safe-concurrency.json")
 DEFAULT_DJEN_CONCURRENCY = 4
+SAVE_INTERVAL_SECONDS = 180.0
+IA_UPLOAD_INTERVAL_SECONDS = 600.0
 
 
 def load_djen_safe_concurrency() -> int:
@@ -470,8 +472,15 @@ async def run_pipeline(
 
     circuit_breaker = CircuitBreaker()
     last_save = last_ia_upload = time.monotonic()
-    save_interval, ia_upload_interval = 180.0, 600.0
+    save_interval, ia_upload_interval = SAVE_INTERVAL_SECONDS, IA_UPLOAD_INTERVAL_SECONDS
     checkers_done = asyncio.Event()
+    # Fire-and-forget asyncio.create_task() calls keep no strong reference
+    # of their own -- per the asyncio docs the event loop only holds a weak
+    # one, so an unreferenced task may be garbage-collected mid-flight.
+    # Tracking every background upload task here and joining them before
+    # run_pipeline returns keeps the periodic-upload safety net (CLAUDE.md:
+    # "protects against crashes") from being silently abandoned at shutdown.
+    background_tasks: set[asyncio.Task[None]] = set()
 
     last_stats_log = last_notify = time.monotonic()
     stats_log_interval, notify_interval = 30.0, 0.5
@@ -586,7 +595,9 @@ async def run_pipeline(
                 manifest.save_to_disk(config.manifest_file)
             if time.monotonic() - last_ia_upload > ia_upload_interval and not config.dry_run:
                 last_ia_upload = time.monotonic()
-                asyncio.create_task(_upload_manifest_background())
+                bg_task = asyncio.create_task(_upload_manifest_background())
+                background_tasks.add(bg_task)
+                bg_task.add_done_callback(background_tasks.discard)
 
     async def download_worker(client: httpx.AsyncClient) -> None:
         while not abort_event.is_set() and not deadline_event.is_set():
@@ -718,6 +729,9 @@ async def run_pipeline(
             with contextlib.suppress(asyncio.CancelledError):
                 await monitor_task
 
+            if background_tasks:
+                await asyncio.gather(*background_tasks, return_exceptions=True)
+
             if circuit_breaker.was_opened:
                 log.warning(
                     "pipeline_completed_with_throttling",
```

Novo arquivo `tests/djen_backup/test_background_manifest_upload.py` (1 teste): dispara `run_pipeline` com `IA_UPLOAD_INTERVAL_SECONDS` zerado e `dry_run=False`, mocka `SyncManifest.upload_segment_to_ia`/`upload_summary_to_ia` para bloquear num `asyncio.Event` controlado pelo teste, e prova que `run_pipeline` permanece pendente enquanto o upload de fundo está em voo, só retornando (com o upload de fato concluído) depois que o teste libera o `Event`.
