---
goal: "Fix SyncManifest.apply_event/_normalize_event so an 'absent' djen_status with an empty djen_raw is downgraded to unknown, matching the CLAUDE.md invariant already enforced by the legacy CSV loader (_load_manifest_line) but missing from the canonical parquet+segment event path."
id: "run-goals/20260907t182546z-do-the-best-useful-work-availab/goal-fix-absent-empty-raw-normalization"
kind: "task-advance"
rationale: "CLAUDE.md documents this exact invariant ('Don't trust absent from old runs... reset all absent entries where djen_raw is empty to unknown') and the legacy CSV loader already implements it, but apply_event -- the canonical read path for sync-manifest.parquet + manifest-log/ segments -- has no equivalent guard, so an unverifiable absent+empty-raw event (e.g. a stray manifest-log segment row) is trusted verbatim and would misreport genuine unknown coverage as confirmed-absent in counts()/causaganha_status."
run: "runs/20260907T182546Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "A RED test (test_apply_event_resets_absent_with_empty_raw_to_unknown) fails before the fix and passes after; full pytest -q, ruff check, and ruff format --check stay green; a PR is opened carrying the fix."
type: "RunGoal"
---

# RunGoal
