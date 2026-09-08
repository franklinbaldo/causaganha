---
type: "RunReading"
id: "run-readings/20260908t004159z-confirmar-merge-da-pr-1297-e-ar/reading-experiences"
run: "runs/20260908T004159Z-confirmar-merge-da-pr-1297-e-arquivar-o-handoff"
kind: "experiences"
subject: "This same-day round-family's recent Experience runs"
reference: ".wisk/knowledge/experiences/runs/"
finding: "Run 20260908T002654Z found .wisk/knowledge's managed bootstrap surface not yet materialized on this fresh container checkout (mirroring 20260907T222723Z's identical finding) and re-ran 'wisk init .'; then merged PR #1296 (sibling's DJEN Retry-After fix) and, with the issue backlog and handoff queue both empty, audited djen_backup's 'reset' CLI command. Found src/djen_backup/service.py's reset_manifest() cleared ia_status/djen_status/updated_at but left djen_raw untouched, even though engine.py's check-priority builder deliberately trusts djen_raw (not djen_status) as the terminal signal -- so 'reset' silently no-op'd for exactly the entries an operator would run it against. Fixed via RED->GREEN TDD, landed as PR #1297 (squash 53cfe59), merged this round after an update_pull_request_branch call moved mergeable_state from behind to clean."
---

# RunReading
