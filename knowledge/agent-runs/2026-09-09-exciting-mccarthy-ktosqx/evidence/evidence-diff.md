---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-ktosqx-evidence-diff"
run_id: "2026-09-09-exciting-mccarthy-ktosqx"
goal_id: "2026-09-09-exciting-mccarthy-ktosqx-goal-datedetail-page-probe-cap"
kind: "diff"
reference: "web/src/components/DateDetail.svelte"
summary: "Minimal, local diff: replaces the single Array.from({length:30}) HEAD-probe with a while-loop that probes in batches of 30, accumulating every valid page number and stopping at the first batch that comes back with any gap (fewer than 30 valid probes). Behavior for the pre-existing <=30-page case is unchanged (identical single-batch round trip, identical result); only the >30-page case gains correct discovery. No other file touched besides the new test."
---

# Evidência: diff

```diff
--- a/web/src/components/DateDetail.svelte
+++ b/web/src/components/DateDetail.svelte
@@ -127,16 +127,31 @@
           itemFileCount = dataFiles.length;
         }
 
-        // Probe pages
-        const probes = await Promise.all(
-          Array.from({ length: 30 }, (_, i) => i + 1).map(async (n) => {
-            try {
-              const res = await fetchWithRetry(jsonUrl(n), { method: 'HEAD', redirect: 'follow' });
-              return res.ok ? n : null;
-            } catch { return null; }
-          })
-        );
-        const valid = probes.filter(Boolean) as number[];
+        // Probe pages in growing batches: a fixed cap here would silently
+        // truncate a (tribunal, date) pair with more than PROBE_BATCH_SIZE
+        // shard files -- i.e. more than PROBE_BATCH_SIZE * PUBS_PER_PAGE
+        // publications -- plausible for a high-volume tribunal or a
+        // backlog-catch-up day. Keep probing full-size batches while the
+        // previous batch came back completely valid; a batch with any gap
+        // means no further shard exists beyond it.
+        const PROBE_BATCH_SIZE = 30;
+        const valid: number[] = [];
+        let batchStart = 1;
+        while (true) {
+          const batchNumbers = Array.from({ length: PROBE_BATCH_SIZE }, (_, i) => batchStart + i);
+          const batchProbes = await Promise.all(
+            batchNumbers.map(async (n) => {
+              try {
+                const res = await fetchWithRetry(jsonUrl(n), { method: 'HEAD', redirect: 'follow' });
+                return res.ok ? n : null;
+              } catch { return null; }
+            })
+          );
+          const validInBatch = batchProbes.filter(Boolean) as number[];
+          valid.push(...validInBatch);
+          if (validInBatch.length < PROBE_BATCH_SIZE) break;
+          batchStart += PROBE_BATCH_SIZE;
+        }
         totalPages = valid.length;
 
         // Load target page
```
