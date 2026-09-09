---
type: "RunEvidence"
id: "run-evidence/20260909t002535z-do-the-best-useful-work-availab/evidence-green-diff-fix"
run: "runs/20260909T002535Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "diff: src/causaganha/consolidate/cli.py, tests/consolidate/test_cli_importable.py, tests/consolidate/test_cli_dry_run_manifest.py"
summary: "Fixed the import-breaking typer.Option call (now typer.Option(False, \"--force\", help=...), matching the file's own convention used by every other option). All 3 test_cli_importable.py cases now pass, and every subcommand's --help (date, tribunal-year, backfill, reconsolidate, reconsolidate --force) builds and exits 0 via a live 'uv run python -m causaganha.consolidate <cmd> --help' invocation. Fixing the import unblocked verifying the audit's original lead: _uploads_complete() gated the dry-run manifest write on stats['uploaded']==expected, but stats['uploaded'] is never incremented in dry-run (nothing is actually uploaded), so the manifest-registration path the code's own comment describes ('for dry runs ... we can still register stats of non-empty tables to manifest') was unreachable whenever there was real, non-empty data. Added a dry_run parameter to _uploads_complete: in dry-run mode completeness is export_failures==0 rather than an unreachable upload count. A RED test (test_cli_dry_run_manifest.py) built a real DuckDB comunicacoes row via causaganha.consolidate.transforms.init_tables, ran the real _export_upload_and_manifest with dry_run=True end-to-end (real export_table_sync + validate_parquet, only update_consolidation_manifest mocked to a spy), and asserted marker_uploaded==1 and update_consolidation_manifest was called with the real table stats -- failed before the fix (marker_uploaded stayed 0, manifest never called, logged 'marker_blocked_by_incomplete_uploads'), passed after."
goal: "goal-audit-unswept-modules"
---

# RunEvidence
