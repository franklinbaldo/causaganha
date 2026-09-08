---
goal: "Extract the duplicated absent-self-consistency normalization rule out of SyncManifest._normalize_event (src/djen_backup/manifest.py) and render_manifest_parquet._normalize_manifest (scripts/render_manifest_parquet.py) into one shared, tested source of truth."
id: "run-goals/20260908t122713z-do-the-best-useful-work-availab/goal-extract-shared-absent-consistency"
kind: "task-advance"
rationale: "17 open issues remain the same long-blocked backlog per wiki history (GPU/annotation, infra hosting, IAS3 credentials, TSE Akamai 403, self-deprioritized -- re-verified this round, no new signal). The one open PR (#1322) belongs to a concurrent sibling session's own branch, not this session's to touch. The prior round's own outcome (run 20260908T114022Z) explicitly deferred this exact extraction as its next_move after landing PR #1323, having found this was the second independent instance of the same Python/DuckDB-SQL duplicated-classification-logic pattern (first instance: drain_unknowns.py vs engine.py, PR #1315)."
run: "runs/20260908T122713Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "New tests pass proving manifest.py and render_manifest_parquet.py both derive their absent+djen_raw normalization from one shared module (constants + a pure function), plus a fixture-driven cross-consistency test asserting the DuckDB-SQL path and the Python path agree on the same representative rows; full pytest suite green; ruff clean; PR opened."
type: "RunGoal"
---

# RunGoal
