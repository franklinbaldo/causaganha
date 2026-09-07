---
goal: "Add missing test coverage to the newly-published human-facing 'causaganha' CLI (src/causaganha_cli, PR #1258, shipped to PyPI as 1.0.3) and fix any real defect the tests surface."
id: "run-goals/20260907t082458z-fa-a-o-melhor-avan-o-poss-vel-n/goal-test-and-fix-causaganha-cli"
kind: "task-advance"
rationale: "No open PRs exist and all 17 open GitHub issues remain independently blocked (knowledge/backlog/, re-verified: ML/GPU work, missing IAS3 credentials, or an infra decision only the repo owner can make) — re-checked this round via 'env | grep -iE IAS3|IA_ACCESS|IA_SECRET|ARCHIVE' (empty) and knowledge/backlog/issue-*.md. Main is green (ruff, ruff format, full pytest all clean at HEAD). src/causaganha_cli/__main__.py is the only shipped-to-PyPI product surface in the repo with zero test files anywhere under tests/, a genuine and independently-discoverable gap, chosen over inventing speculative new features."
run: "runs/20260907T082458Z-fa-a-o-melhor-avan-o-poss-vel-no-reposit-rio-fra"
status: "carried_forward"
success_signal: "A new tests/causaganha_cli/test_causaganha_cli_main.py exists covering _connection (network boundary, success and HTTP-error propagation) and both CLI commands (query, comunicacoes) including output-format validation, limit bounds, tribunal filtering and SQL-quote escaping. Running it red-then-green: before the fix, test_comunicacoes_rejects_invalid_output_format fails with 'DID NOT RAISE ValueError' (comunicacoes silently accepted output=\"xml\" while query correctly rejects it) demonstrating a genuine behavioral inconsistency; after adding the same output validation comunicacoes already has for limit, all 13 tests pass, and 'TRIBUNAL=tjro uv run pytest -q' plus 'ruff check'/'ruff format --check' stay green across the whole repo."
type: "RunGoal"
---

# RunGoal
