---
type: "RunReading"
id: "run-readings/20260910t164424z-confirmar-merge-da-pr-1427-e-ar/reading-experiences"
run: "runs/20260910T164424Z-confirmar-merge-da-pr-1427-e-arquivar-o-handoff"
kind: "experiences"
subject: ".wisk/knowledge/experiences/records/20260907T062555Z-human-cli-prs-merged.md"
reference: ".wisk/knowledge/experiences/records/20260907T062555Z-human-cli-prs-merged.md"
finding: "Only one Experience record exists in the bundle (2026-09-07, about merging PRs #1261/#1258 -- Actions-API check-run reads can lag reality, so a mutating call or list_workflow_runs is faster than repeated polling). Did not apply this round: PR #1427's checks were read fresh via pull_request_read across two events (check_suite.completed at 16:41 and 16:43) and were genuinely complete (9/9 success, mergeable_state clean) before merging, no stale-read symptoms."
---

# RunReading
