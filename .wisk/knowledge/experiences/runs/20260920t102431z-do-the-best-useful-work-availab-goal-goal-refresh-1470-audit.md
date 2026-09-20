---
type: "RunGoal"
id: "run-goals/20260920t102431z-do-the-best-useful-work-availab/goal-refresh-1470-audit"
run: "runs/20260920T102431Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Re-run scripts/audit_cnj_parquets.py end-to-end to produce a fresh 2026-09-20 catalog audit report, and use it to close issue #1470's outstanding 're-run before rollout, document unavailable files without calling them absent' acceptance-criterion item."
rationale: "The 2026-09-14 evidence file was 6 days stale; #1470 is the only currently open catalog-audit task with zero external-credential dependency (archive.org public metadata/search API only), it directly unblocks the #1468/#1469/#1471/#1472 CNJ-reordering epic's rollout decision, and #1471/#1482/#950 were all found this round to have no remaining credential-free code work."
success_signal: "A committed docs/planning/evidence/audit-cnj-parquets-2026-09-20.json exists with a per-item classification breakdown; any read-error/unavailable files are explicitly reported as 'unavailable' (never 'absent'); issue #1470 receives a comment summarizing the delta against 2026-09-14 and, if all checklist items are now satisfied, is proposed for closure."
status: "active"
---

# RunGoal
