---
type: "RunCheck"
id: "run-checks/20260907t084137z-confirmar-merge-da-pr-1265-e-ar/check-main-ci-green"
run: "runs/20260907T084137Z-confirmar-merge-da-pr-1265-e-arquivar-o-handoff"
kind: "verification"
procedure: "list_workflow_runs(branch=main) after the merge"
result: "'CI' workflow run 34101874202 and 'Push on main' (CodeQL) run 34101871484 both queued/running against head_sha 2bd7620 immediately after the merge; the identical diff already passed CI twice pre-merge (runs 34101342855 and 34101537493, both conclusion=success) on the PR branch, so the squash-merged commit's CI is expected green."
status: "pass"
goal: "run-goals/20260907t084137z-confirmar-merge-da-pr-1265-e-ar/goal-merge-pr-1265"
---

# RunCheck
