---
type: "RunEvidence"
id: "run-evidence/20260920t102431z-do-the-best-useful-work-availab/audit-refresh-2026-09-20"
run: "runs/20260920T102431Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "uv run python scripts/audit_cnj_parquets.py --output docs/planning/evidence/audit-cnj-parquets-2026-09-20.json (ran ~6 min against live archive.org public metadata/search API, no credentials); diffed against docs/planning/evidence/audit-cnj-parquets-2026-09-14.json; posted https://github.com/franklinbaldo/causaganha/issues/1470#issuecomment-5749291780"
summary: "file_count grew 24->61 with zero files disappearing and zero unavailable/verify_values entries. 5 files transitioned reorder_candidate->conformant (djen-tjro-2025, djen-tjto-2025 x2, djen-tjse-2025 x2), evidencing real #1469 writer-regeneration progress. 37 newly-published tribunal-year files appeared since 09-14, most already certified conformant at publish time. reorder_candidate count declined 15->10; verified_unsorted unchanged at 8 (same 4 items)."
goal: "run-goals/20260920t102431z-do-the-best-useful-work-availab/goal-refresh-1470-audit"
---

# RunEvidence
