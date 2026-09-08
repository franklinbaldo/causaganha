---
goal: "Fix _normalize_manifest's SQL downgrade (scripts/render_manifest_parquet.py) to write djen_status='' instead of SQL NULL when downgrading unverifiable-absent rows, matching djen_backup.absent_consistency.normalize_absent's own contract. Also fix the parity test that currently masks this exact divergence by coercing NULL to '' before comparing."
id: "run-goals/20260908t142456z-do-the-best-useful-work-availab/goal-fix-normalize-manifest-null-vs-empty"
kind: "task-advance"
rationale: "Real, currently-live regression from this session-family's own immediately-preceding merged PR (#1325), which was written to prevent SQL/Python drift on this rule but introduced a new NULL-vs-empty-string drift instead. Affects the public /stats totals card and tribunal coverage table: downgraded rows vanish from every bucket while still counting toward total, breaking uploaded+pending+absent+unknown==total."
run: "runs/20260908T142456Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "totals.qmd and tribunal_coverage.qmd's bucket-sum-equals-total invariant holds (RED->GREEN test) for a manifest row with djen_status IS NULL; the parity test in test_absent_consistency_shared.py compares the real SQL value with no '' coercion and passes; full suite + ruff green; PR opened and merged."
type: "RunGoal"
---

# RunGoal
