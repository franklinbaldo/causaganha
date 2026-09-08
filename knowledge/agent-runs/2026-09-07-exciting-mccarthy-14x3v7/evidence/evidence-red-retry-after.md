---
type: AgentEvidence
id: "2026-09-07-exciting-mccarthy-14x3v7-evidence-red-retry-after"
run_id: "2026-09-07-exciting-mccarthy-14x3v7"
goal_id: "2026-09-07-exciting-mccarthy-14x3v7-goal-djen-retry-after-floor"
kind: "test_red"
reference: "web/src/components/__steps__/djen-search.steps.ts::honors a short Retry-After instead of flooring it to 60s"
summary: "Added the new vitest case (mocked 429 response, header retry-after: 5, asserting DjenRateLimitError.retryAfterSec === 5) against the unmodified web/src/lib/djenClient.ts. `npx vitest run src/components/__steps__/djen-search.steps.ts -t \"honors a short Retry-After\"` failed: AssertionError expected retryAfterSec: 5, received retryAfterSec: 60 — confirming the Math.max(60, retryAfterSec) floor is live and reachable exactly as diagnosed."
---

# Evidência RED

```
FAIL  src/components/__steps__/djen-search.steps.ts > searchDjenComunicacoes > honors a short Retry-After instead of flooring it to 60s
AssertionError: expected DjenRateLimitError: ... { retryAfterSec: … } to match object { name: 'DjenRateLimitError', …(1) }
- Expected
+ Received
- {
+ DjenRateLimitError {
    "name": "DjenRateLimitError",
-   "retryAfterSec": 5,
+   "retryAfterSec": 60,
  }
```

Confirma que, com `Retry-After: 5` do servidor, o código atual (`Math.max(60, retryAfterSec)`) devolve 60, não 5.
