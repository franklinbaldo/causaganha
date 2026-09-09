---
type: "RunCheck"
id: "run-checks/20260909t004854z-do-the-best-useful-work-availab/check-full-suite"
run: "runs/20260909T004854Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q; uv run ruff check; uv run ruff format --check; grep -rn typer src/ scripts/ --include=*.py; live: python -m causaganha.consolidate {date,tribunal-year,backfill,reconsolidate}[--force] --help; uv run segmenter-dataset {assign-splits,build-release,render-dataset-card} --help"
result: "Full pytest suite green (grew by 10 tests: 9 new tests/segmenter_dataset/test_cli_contract.py cases + 1 net after test_cli_importable.py's empty-invocation assertion changed in place). ruff check: All checks passed. ruff format --check: 401 files already formatted. grep for 'import typer'/'from typer' under src/ and scripts/: zero matches (excluding __pycache__). Every subcommand of both migrated CLIs (consolidate: date/tribunal-year/backfill/reconsolidate/reconsolidate --force; segmenter-dataset: assign-splits/build-release/render-dataset-card, plus the real installed 'segmenter-dataset' console script) builds and exits 0 on --help, verified live via direct process invocation, not just the test harness."
status: "pass"
evidence: "evidence-diff-migration"
goal: "goal-migrate-typer-to-cyclopts"
---

# RunCheck
