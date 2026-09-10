---
type: "RunEvidence"
id: "run-evidence/20260910t035530z-do-the-best-useful-work-availab/evidence-diff-and-green"
run: "runs/20260910T035530Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "git diff --stat (14 deletions across 4 files: engine.py SyncConfig, service.py PipelineRunConfig + its pass-through, __main__.py's 3 subcommand call sites, tests/cli_contract/test_semantic_argv_contract.py's expected-config equality check); GREEN via 'python -m pytest tests/djen_backup/test_dead_config_fields_removed.py tests/cli_contract/ tests/djen_backup/ -q'"
summary: "Deleted both fields and every construction-site reference; no behavior code changed since neither field was ever read. New RED test now passes GREEN, full tests/djen_backup/ suite (121 tests) and tests/cli_contract/ suite both green, ruff check/format clean on all touched files. Confirmed via grep -rn across src/ and tests/ (excluding .wisk/ and __pycache__) that no other reference to either field name remains anywhere in the codebase."
goal: "goal-remove-dead-config-flags"
---

# RunEvidence
