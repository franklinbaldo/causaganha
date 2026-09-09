---
type: "RunCheck"
id: "run-checks/20260909t002535z-do-the-best-useful-work-availab/check-full-suite"
run: "runs/20260909T002535Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q; uv run ruff check; uv run ruff format --check; uv run python -m causaganha.consolidate {date,tribunal-year,backfill,reconsolidate} --help; uv run python -m causaganha.consolidate reconsolidate --force --help"
result: "Full Python suite green (all tests pass, 1 pre-existing skip, no new failures). New tests/consolidate/ files add 4 cases (test_cli_importable.py x3, test_cli_dry_run_manifest.py x1), full tests/consolidate/ directory: 24 passed. ruff check: All checks passed. ruff format --check: 400 files already formatted. Every consolidate CLI subcommand's --help now builds and exits 0, including reconsolidate --force --help (previously impossible -- the module could not even import)."
status: "pass"
evidence: "evidence-green-diff-fix"
goal: "goal-audit-unswept-modules"
---

# RunCheck
