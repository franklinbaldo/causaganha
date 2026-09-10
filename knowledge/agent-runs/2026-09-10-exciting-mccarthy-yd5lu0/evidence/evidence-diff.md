---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-yd5lu0-evidence-diff"
run_id: "2026-09-10-exciting-mccarthy-yd5lu0"
goal_id: "2026-09-10-exciting-mccarthy-yd5lu0-goal-download-zip-cancels-siblings"
kind: "diff"
reference: "git diff src/djen_backup/djen.py (this session's working tree) + new file tests/djen_backup/test_download_zip_segment_cancellation.py"
summary: "download_zip now wraps each segment coroutine in asyncio.ensure_future so it holds a cancellable Task reference, and wraps asyncio.gather(*tasks) in a try/except BaseException that cancels and drains every task before re-raising the original exception unchanged. New test file tests/djen_backup/test_download_zip_segment_cancellation.py (1 test) proves siblings are cancelled, not left orphaned."
---

# Evidência diff

```diff
diff --git a/src/djen_backup/djen.py b/src/djen_backup/djen.py
index 61152b8..474e347 100644
--- a/src/djen_backup/djen.py
+++ b/src/djen_backup/djen.py
@@ -199,9 +199,20 @@ async def download_zip(
     for i in range(DOWNLOAD_SEGMENTS):
         start = i * segment_size
         end = total_size - 1 if i == DOWNLOAD_SEGMENTS - 1 else (i + 1) * segment_size - 1
-        tasks.append(_download_segment(client, url, start, end))
+        tasks.append(asyncio.ensure_future(_download_segment(client, url, start, end)))
 
-    segments = await asyncio.gather(*tasks)
+    try:
+        segments = await asyncio.gather(*tasks)
+    except BaseException:
+        # asyncio.gather does not cancel sibling tasks when one fails --
+        # left alone they keep running in the background after this
+        # function has already propagated the failure, wasting DJEN
+        # rate-limit budget and connections on a download nobody awaits
+        # the result of anymore. Cancel and drain them before re-raising.
+        for task in tasks:
+            task.cancel()
+        await asyncio.gather(*tasks, return_exceptions=True)
+        raise
 
     # Write all segments to temp file
     with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
```

New file `tests/djen_backup/test_download_zip_segment_cancellation.py` (1 test): monkeypatches `_download_segment` so one segment raises immediately and the other three block on an unset `asyncio.Event` (never resolves except via cancellation), then asserts all three are cancelled and none completes after `download_zip` propagates the failure.
