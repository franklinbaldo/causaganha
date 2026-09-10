---
type: "RunCheck"
id: "run-checks/20260910t033931z-do-the-best-useful-work-availab/check-full-suite-and-ruff"
run: "runs/20260910T033931Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "python -m pytest -q (full repo suite, ~1900+ tests, run via a pip-based venv since 'uv run' itself needs network access to build the wisk/opf git dependency-group sdists that this sandbox's uv resolution could not complete in reasonable time); ruff check + ruff format --check on the changed files"
result: "1917 passed, 1 skipped, 1 failed. The sole failure (test_agent_stdio_recipe.py::test_published_stdio_recipe_works_from_outside_checkout) is pre-existing and unrelated to this change: it shells out to 'uv run' itself to simulate an outside-checkout MCP client, which fails in this sandbox with 'invalid peer certificate: UnknownIssuer' while trying to build the wisk git dependency via uv -- the same network/TLS limitation this round worked around for its own tooling by using pip instead of uv. Confirmed via 'git log -1' that this test file predates this round's change (commit 63428b0) and touches only the MCP stdio server, nothing in src/djen_backup/. ruff check and ruff format --check are clean on src/djen_backup/engine.py and the new test file."
status: "pass"
evidence: "evidence-diff-and-green"
goal: "goal-upload-only-no-djen-check"
---

# RunCheck
