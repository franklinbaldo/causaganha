---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-aezdb9-evidence-diff"
run_id: "2026-09-10-exciting-mccarthy-aezdb9"
goal_id: "2026-09-10-exciting-mccarthy-aezdb9-goal-ia-rate-limit-fallback"
kind: "diff"
reference: "git diff src/djen_backup/archive.py (pre-PR, this session's working tree) + new file tests/djen_backup/test_ia_rate_limit_parsing.py"
summary: "Replaced the module-level try/except int() parse with a `_parse_ia_max_rate(raw, default=4)` pure function that also rejects value <= 0, falling back to the default for both non-numeric and non-positive input. Added tests/djen_backup/test_ia_rate_limit_parsing.py (5 tests)."
---

# Evidência diff

```diff
diff --git a/src/djen_backup/archive.py b/src/djen_backup/archive.py
index e285204..1a2b3c4 100644
--- a/src/djen_backup/archive.py
+++ b/src/djen_backup/archive.py
@@ -55,12 +55,29 @@ _item_locks: dict[str, asyncio.Lock] = {}
 _item_locks_guard = asyncio.Lock()
 
-# Rate limit: ~1 upload / 2 s steady-state, burst of 4 by default.
-# Can be overridden via the IA_UPLOAD_RATE_LIMIT environment variable.
-# NOTE: This is initialized at module import time; changing the env var
-# mid-process will not take effect.
-try:
-    _ia_max_rate = int(os.environ.get("IA_UPLOAD_RATE_LIMIT", "4"))
-except ValueError:
-    _ia_max_rate = 4
+_IA_UPLOAD_RATE_LIMIT_DEFAULT = 4
+
+
+def _parse_ia_max_rate(raw: str | None, default: int = _IA_UPLOAD_RATE_LIMIT_DEFAULT) -> int:
+    """Parse the ``IA_UPLOAD_RATE_LIMIT`` env var, falling back on bad input.
+
+    Falls back to ``default`` both for a value that isn't an integer and for
+    one that is but isn't positive (``0`` or negative). A non-positive
+    ``max_rate`` would make every ``AsyncLimiter.acquire()`` call raise
+    ``ValueError`` (it requires ``0 <= amount <= max_rate``), which nothing
+    in ``upload_zip``'s caller chain catches -- so a bad value must never
+    reach ``AsyncLimiter`` in the first place.
+    """
+    if raw is None:
+        return default
+    try:
+        value = int(raw)
+    except ValueError:
+        return default
+    if value <= 0:
+        return default
+    return value
+
+
+# Rate limit: ~1 upload / 2 s steady-state, burst of 4 by default.
+# Can be overridden via the IA_UPLOAD_RATE_LIMIT environment variable.
+# NOTE: This is initialized at module import time; changing the env var
+# mid-process will not take effect.
+_ia_max_rate = _parse_ia_max_rate(os.environ.get("IA_UPLOAD_RATE_LIMIT"))
 
 _IA_RATE_LIMITER = AsyncLimiter(max_rate=_ia_max_rate, time_period=8)
```

New file `tests/djen_backup/test_ia_rate_limit_parsing.py` (5 tests): valid positive value used as-is; missing env var, non-numeric string, `"0"`, and `"-1"` all fall back to the default of 4.
