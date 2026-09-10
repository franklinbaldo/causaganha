---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-r3erpr-evidence-diff"
run_id: "2026-09-10-exciting-mccarthy-r3erpr"
goal_id: "2026-09-10-exciting-mccarthy-r3erpr-goal-cb-probe-lock-order"
kind: "diff"
reference: "git diff src/djen_backup/archive.py (pre-PR, this session's working tree)"
summary: "Moved the `lock = await _lock_for(item_id)` / `if try_lock and lock.locked(): raise ItemBusyError(item_id)` block to run before `circuit_breaker.allow_request()` instead of after, with an explanatory comment. No behavior change for the non-busy path. New test file tests/djen_backup/test_circuit_breaker_lock_interaction.py (1 test)."
---

# Evidência diff

```
diff --git a/src/djen_backup/archive.py b/src/djen_backup/archive.py
index 0e0b214..e285204 100644
--- a/src/djen_backup/archive.py
+++ b/src/djen_backup/archive.py
@@ -244,6 +244,18 @@ async def upload_zip(
 
     Returns ``True`` on success, ``False`` on failure or open circuit.
     """
+    # Check the per-item lock *before* the circuit breaker: a HALF_OPEN
+    # breaker's allow_request() atomically consumes its one test-probe slot,
+    # expecting the caller to actually attempt IA and report the result. A
+    # busy item never gets that far (ItemBusyError short-circuits below), so
+    # checking allow_request() first would burn the probe on a call that
+    # never touched IA -- leaving the breaker OPEN for a full recovery
+    # window with no test performed. The lock check has no side effects, so
+    # it costs nothing to do it first.
+    lock = await _lock_for(item_id)
+    if try_lock and lock.locked():
+        raise ItemBusyError(item_id)
+
     if circuit_breaker is not None and not await circuit_breaker.allow_request():
         log.warning("upload_skipped_circuit_open", item_id=item_id)
         return False
@@ -252,9 +264,6 @@ async def upload_zip(
     stem_parts = zip_path.stem.split("-")
     date_str = f"{stem_parts[1]}-{stem_parts[2]}-{stem_parts[3]}" if len(stem_parts) >= 4 else ""
 
-    lock = await _lock_for(item_id)
-    if try_lock and lock.locked():
-        raise ItemBusyError(item_id)
     async with lock:
         await _IA_RATE_LIMITER.acquire()  # aiolimiter supports .acquire() or async with
         start = time.monotonic()
```
