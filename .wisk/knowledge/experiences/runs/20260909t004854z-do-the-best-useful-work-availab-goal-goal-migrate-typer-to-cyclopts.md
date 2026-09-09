---
goal: "Migrate the two remaining Typer CLIs (src/causaganha/consolidate/cli.py and src/segmenter_dataset/__main__.py) to Cyclopts, matching RFC 0013's already-migrated packages (djen_backup, tjro_juris, stj_acordaos, datajud) in conventions (Parameter(negative=[]) for flags that had no negation, / and * to preserve positional/keyword-only distinctions, cyclopts.validators.Path/Number for exists=True/file_okay=False/min= constraints, version_flags=[], explicit help+exit-2 default for empty invocation where the Typer original used no_args_is_help), then drop typer entirely from pyproject.toml dependencies."
id: "run-goals/20260909t004854z-do-the-best-useful-work-availab/goal-migrate-typer-to-cyclopts"
kind: "task-advance"
rationale: "Live, explicit user instruction: 'vamos substituir o typer por cyclopts em todo o app' (let's replace typer with cyclopts throughout the whole app). RFC 0013 already migrated 4 of 6 Typer CLIs and explicitly deferred these two as out of its scope (neither is invoked by any GitHub Actions workflow, confirmed via grep) -- this finishes that migration rather than starting a new one from scratch."
run: "runs/20260909T004854Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "Neither src/segmenter_dataset/__main__.py nor src/causaganha/consolidate/cli.py imports typer; 'typer' is removed from pyproject.toml's dependency list and 'import typer'/'from typer' returns zero matches under src/ and scripts/ (excluding __pycache__/generated files); every existing and newly-added test (module-import smoke tests plus behavior-preserving characterization tests written before migrating each file) passes; full pytest/ruff check/ruff format --check stay green."
type: "RunGoal"
---

# RunGoal
