---
type: "RunCheck"
id: "run-checks/20260908t085404z-do-the-best-useful-work-availab/check-pr-1315-grounding"
run: "runs/20260908T085404Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "pull_request_read(get, #1315); pull_request_read(get_check_runs, #1315); git fetch origin main; git show origin/main:scripts/drain_unknowns.py | grep HTTP_OK"
result: "merged=true, squash sha a00561f6; 9/9 check runs conclusion=success; grep confirms the fix landed on origin/main's tip."
status: "pass"
evidence: "run-evidence/20260908t085404z-do-the-best-useful-work-availab/evidence-pr-1315-merged"
goal: "run-goals/20260908t085404z-do-the-best-useful-work-availab/goal-confirm-pr-1315-merge"
---

# RunCheck
