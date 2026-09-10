---
type: "RunReading"
id: "run-readings/20260910t153950z-do-the-best-useful-work-availab/reading-experiences"
run: "runs/20260910T153950Z-do-the-best-useful-work-available-in-this-reposi"
kind: "experiences"
subject: ".wisk/knowledge/experiences/records/20260907T062555Z-human-cli-prs-merged.md"
reference: ".wisk/knowledge/experiences/records/20260907T062555Z-human-cli-prs-merged.md"
finding: "Only one Experience record exists in the bundle (2026-09-07, about merging PRs #1261/#1258). Its operational note -- Actions-API check-run reads can lag reality by minutes, so a mutating call (merge attempt) or list_workflow_runs reflects true state faster than repeated check-run polling -- did not apply this round: PR #1425's checks were read fresh via pull_request_read and were genuinely complete (9/9 success, mergeable_state clean) before merging, with no stale-read symptoms observed."
---

# RunReading
