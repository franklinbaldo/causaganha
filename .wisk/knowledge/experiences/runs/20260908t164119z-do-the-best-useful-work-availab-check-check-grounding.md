---
type: "RunCheck"
id: "run-checks/20260908t164119z-do-the-best-useful-work-availab/check-grounding"
run: "runs/20260908T164119Z-do-the-best-useful-work-available-in-this-reposi"
kind: "grounding"
procedure: "pull_request_read(get, PR #1332) + git log -1 origin/main -- web/src/lib/coverageInsights.ts"
result: "Both primary-source checks confirm the wiki update's claims: GitHub API reports PR #1332 merged=true, merged_by=franklinbaldo, merged_at=2026-09-08T16:40:29Z; git's own history on origin/main shows e22b818 as the sole and most recent commit touching coverageInsights.ts, matching the recorded squash SHA exactly (no transcription error)."
status: "pass"
evidence: "run-evidence/20260908t164119z-do-the-best-useful-work-availab/evidence-invariants-extended"
goal: "run-goals/20260908t164119z-do-the-best-useful-work-availab/goal-confirm-pr-1332-and-extend-invariants"
---

# RunCheck
