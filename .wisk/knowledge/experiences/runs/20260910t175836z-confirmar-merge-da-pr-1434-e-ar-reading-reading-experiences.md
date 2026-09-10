---
type: "RunReading"
id: "run-readings/20260910t175836z-confirmar-merge-da-pr-1434-e-ar/reading-experiences"
run: "runs/20260910T175836Z-confirmar-merge-da-pr-1434-e-arquivar-o-handoff"
kind: "experiences"
subject: ".wisk/knowledge/experiences/records/20260907T062555Z-human-cli-prs-merged.md"
reference: ".wisk/knowledge/experiences/records/20260907T062555Z-human-cli-prs-merged.md"
finding: "Only one Experience record exists (2026-09-07, merging PRs #1261/#1258 -- Actions-API check-run reads can lag reality). This round's own experience adds a new, distinct lesson (recorded in the wiki below, not this record): a required-status-check rejection citing a specific check by name can actually mean 'mergeable_state is behind, re-check that field directly' rather than the named check truly being unsatisfied -- the check_runs read showed green while the merge endpoint still rejected until the branch was brought up to date twice against a concurrently-advancing main."
---

# RunReading
