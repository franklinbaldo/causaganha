---
type: "RunReading"
id: "run-readings/20260910t043903z-do-the-best-useful-work-availab/reading-experiences"
run: "runs/20260910T043903Z-do-the-best-useful-work-available-in-this-reposi"
kind: "experiences"
subject: "runs/20260910T042601Z-do-the-best-useful-work-available-in-this-reposi"
reference: "This session's own immediately preceding Experience round"
finding: "That round re-audited fail_fast after the prior round's own outcome (run 20260910T035530Z, PR #1404) claimed it was 'genuinely read/honored' -- found the claim was only half-checked: fail_fast was read and enforced by the upload worker, but download_worker's except block never checked it or set abort_event, contradicting the CLI's own 'Stop on first error' documentation for the more common (download) failure path. Fixed via RED->GREEN TDD (tests/djen_backup/test_download_worker_fail_fast.py), opened PR #1406 from a branch freshly reset to main (avoiding the twentieth pattern's squash-continuation hazard), subscribed to activity."
---

# RunReading
