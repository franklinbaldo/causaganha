---
type: "RunCheck"
id: "run-checks/20260907t082458z-fa-a-o-melhor-avan-o-poss-vel-n/check-full-suite-and-lint"
run: "runs/20260907T082458Z-fa-a-o-melhor-avan-o-poss-vel-no-reposit-rio-fra"
kind: "verification"
procedure: "TRIBUNAL=tjro uv run pytest -q (full repo suite); uv run ruff check; uv run ruff format --check"
result: "Full suite: 2625 passed, 1 skipped, no failures. ruff check: All checks passed. ruff format --check: 388 files already formatted (385 baseline + 3 new/changed: src/causaganha_cli/__main__.py, tests/causaganha_cli/test_causaganha_cli_main.py)."
status: "pass"
evidence: "run-evidence/20260907t082458z-fa-a-o-melhor-avan-o-poss-vel-n/evidence-red-then-green-comunicacoes-output"
goal: "run-goals/20260907t082458z-fa-a-o-melhor-avan-o-poss-vel-n/goal-test-and-fix-causaganha-cli"
---

# RunCheck
