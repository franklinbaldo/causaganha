---
type: "RunReading"
id: "run-readings/20260908t054448z-do-the-best-useful-work-availab/reading-wiki"
run: "runs/20260908T054448Z-do-the-best-useful-work-available-in-this-reposi"
kind: "wiki"
subject: "Existing durable Wisk wiki state"
reference: ".wisk/knowledge/wiki/"
finding: "One WikiEntry exists: continuous-loop-operational-invariants.md, covering: Wisk orchestration owning the loop; the fresh-checkout 'wisk init .' requirement; the GitGuardian required-check/update_pull_request_branch merge pattern; a RunOutcome's next_move as a legitimate work source; the circuit_breaker.py sync/async dual-calling-convention hazard (three instances); reset_manifest's canonical-vs-mirrored-field hazard; and drain.py's missed DJENRateLimitedError catch as a sibling-call-site-exception-handling hazard. None of these cover this round's finding: a human-facing architecture doc (FRONTEND.md) describing files, functions, and a whole subsystem (useDashboard.svelte.ts, buildTimeData.ts, useDashboardWithPolling) that never existed anywhere in the repo, with code samples misattributed to real files verified to use a different, current pattern. Worth adding as a distinct, generalizable category: documentation drift is not limited to knowledge/wiki entries about the loop itself -- a project's own architecture guide needs the same file-existence/call-site verification before being trusted or extended."
---

# RunReading
