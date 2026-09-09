---
type: "RunEvidence"
id: "run-evidence/20260909t002535z-do-the-best-useful-work-availab/evidence-red-cli-broken"
run: "runs/20260909T002535Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "local: uv run pytest tests/consolidate/test_cli_importable.py -v (before fix)"
summary: "An Explore-agent audit of unswept src/causaganha/ modules flagged consolidate/cli.py's dry-run manifest gate; verifying it required importing causaganha.consolidate.cli, which failed at module load: reconsolidate()'s force option used typer.Option(\"--force\", default=False, ...), passing the option name positionally into typer.Option's own 'default' parameter while also passing default=False as a keyword, raising 'TypeError: Option() got multiple values for argument default' at class-definition time. This breaks every subcommand in the module (date, tribunal-year, backfill, reconsolidate) -- python -m causaganha.consolidate cannot run at all. Confirmed a fresh, targeted RED test (tests/consolidate/test_cli_importable.py, 3 cases) fails exactly this way before any fix."
goal: "goal-audit-unswept-modules"
---

# RunEvidence
