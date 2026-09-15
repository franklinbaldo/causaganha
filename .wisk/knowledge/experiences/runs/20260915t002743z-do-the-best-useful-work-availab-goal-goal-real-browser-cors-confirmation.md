---
goal: "Deliver the definitive real-browser CORS confirmation for issue #1482 that handoff-issue-1471-archive-readback-v2's next_action item 3 and PR #1484 both explicitly left undone, and land it as committed evidence + a real regression test so the finding cannot silently regress."
id: "run-goals/20260915t002743z-do-the-best-useful-work-availab/goal-real-browser-cors-confirmation"
kind: "domain"
rationale: "PR #1484 (merged) already shipped the frontend fix for #1482's symptom but stated plainly it could not confirm the CORS block with an actual browser -- only curl/urllib HTTP-header checks, which don't enforce CORS themselves. Closing that gap with real evidence (not another simulation) is a genuine, bounded, credential-free advance available this round, unlike #1471/#1472's IA-publish step."
run: "runs/20260915T002743Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "node scripts/benchmarks/archive_cors_probe.mjs succeeds against real archive.org in this sandbox (previously failed with net::ERR_CERT_AUTHORITY_INVALID) and shows the metadata endpoint succeeding (type: cors) while the download endpoint fails with a real fetch TypeError; the result is committed as JSON evidence and a Vitest regression test encoding the same expectation is added and passes."
type: "RunGoal"
---

# RunGoal
