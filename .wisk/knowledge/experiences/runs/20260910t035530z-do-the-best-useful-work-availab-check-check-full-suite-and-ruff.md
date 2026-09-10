---
type: "RunCheck"
id: "run-checks/20260910t035530z-do-the-best-useful-work-availab/check-full-suite-and-ruff"
run: "runs/20260910T035530Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "python -m pytest -q (full repo suite, ~1920 tests, pip-based venv per this session's established uv-network-limitation workaround); ruff check + ruff format --check on all touched files"
result: "1 failure, the same pre-existing unrelated tests/causaganha_mcp/test_agent_stdio_recipe.py::test_published_stdio_recipe_works_from_outside_checkout (shells out to 'uv run' to build the wisk git dependency, fails on this sandbox's TLS/network limitation -- documented in PR #1403's own body, confirmed unrelated via git log). Everything else passed, including the new tests/djen_backup/test_dead_config_fields_removed.py and the updated tests/cli_contract/test_semantic_argv_contract.py. ruff check and ruff format --check clean on src/djen_backup/{engine,service,__main__}.py and both touched test files."
status: "pass"
evidence: "evidence-diff-and-green"
goal: "goal-remove-dead-config-flags"
---

# RunCheck
