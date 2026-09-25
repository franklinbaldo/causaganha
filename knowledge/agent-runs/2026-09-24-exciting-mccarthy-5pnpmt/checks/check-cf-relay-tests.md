---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-5pnpmt-check-cf-relay-tests"
run_id: "2026-09-24-exciting-mccarthy-5pnpmt"
goal_id: "2026-09-24-exciting-mccarthy-5pnpmt-goal-relay-egress-policy"
evidence_id: "2026-09-24-exciting-mccarthy-5pnpmt-evidence-green-cf-relay"
command: "cd deployment/relay-cf && npm test && npm run check"
result: "passed"
summary: "npm test (vitest sob @cloudflare/vitest-pool-workers, runtime workerd real): 18 passed. npm run check (wrangler deploy --dry-run): builda sem erro, Total Upload 5.42 KiB / gzip 1.85 KiB, sem bindings. package-lock.json revertido apos 'npm install' para nao carregar churn de metadata nao relacionado nesta mudanca."
---

# Check: suite do relay Cloudflare (vitest + wrangler dry-run)

```
$ npm test
Test Files  1 passed (1)
     Tests  18 passed (18)

$ npm run check
Total Upload: 5.42 KiB / gzip: 1.85 KiB
No bindings found.
--dry-run: exiting now.
```
