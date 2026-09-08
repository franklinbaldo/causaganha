---
type: AgentDecision
id: "2026-09-08-exciting-mccarthy-k18r9l-decision-reuse-absent-consistency-constants"
run_id: "2026-09-08-exciting-mccarthy-k18r9l"
goal_id: "2026-09-08-exciting-mccarthy-k18r9l-goal-classify-200-prefix-false-drift"
question: "Fix _classify() by inlining the literal check (`raw == '200' or raw.startswith('200:')`), matching src/djen_backup/manifest.py's own inline style, or import the BARE_200_RAW/PREFIXED_200_RAW_PREFIX constants from src/djen_backup/absent_consistency.py?"
choice: "Import and reuse BARE_200_RAW and PREFIXED_200_RAW_PREFIX from djen_backup.absent_consistency instead of re-typing the '200'/'200:' literals a third time."
rationale: "absent_consistency.py's own module docstring states its explicit purpose: two independent runtimes (SyncManifest._normalize_event and render_manifest_parquet.py's _normalize_manifest) had already drifted once before on this exact rule and were caught only by PR #1323, so the module exists specifically so 'the SQL literals ... must be interpolated from these same constants rather than re-typed.' backfill_probe.py's _classify() is a third, independent re-implementation of the same '200 means available, with or without a detail suffix' rule -- writing it as a fresh literal a third time would recreate the identical drift risk this module was built to prevent. Importing the constants costs one import line and makes the dependency on the canonical rule explicit and typo-proof."
---

# Decisao: reusar constantes de absent_consistency.py em vez de reescrever o literal

Ver `run.md`/`goals/goal-classify-200-prefix-false-drift.md`. `absent_consistency.py` já documenta ter sido criado exatamente para evitar essa 3a reimplementação divergente da mesma regra ("200"/"200:" -> available).
