---
type: "RunEvidence"
id: "run-evidence/20260908t122713z-do-the-best-useful-work-availab/evidence-green-diff"
run: "runs/20260908T122713Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "src/djen_backup/absent_consistency.py, src/djen_backup/manifest.py, scripts/render_manifest_parquet.py, tests/test_absent_consistency_shared.py"
summary: "New src/djen_backup/absent_consistency.py holds the shared constants + normalize_absent(). manifest.py's SyncManifest._normalize_event now delegates to it after its own confirmed->available rewrite. render_manifest_parquet.py's _normalize_manifest builds its two UPDATE statements' literals from the same shared constants (re-exported as ABSENT_SELF_CONSISTENCY_SENTINEL) instead of re-typed strings. uv run pytest tests/test_absent_consistency_shared.py -q -> 8 passed (up from 2 failed/6 passed pre-implementation)."
goal: "run-goals/20260908t122713z-do-the-best-useful-work-availab/goal-extract-shared-absent-consistency"
---

# RunEvidence
