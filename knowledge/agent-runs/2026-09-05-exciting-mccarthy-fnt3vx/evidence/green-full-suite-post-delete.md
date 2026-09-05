---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-fnt3vx-evidence-green-full-suite-post-delete"
run_id: "2026-09-05-exciting-mccarthy-fnt3vx"
goal_id: "2026-09-05-exciting-mccarthy-fnt3vx-goal-purge-dead-experiment-imports"
kind: "test_green"
reference: "uv run ruff check; uv run ruff format --check; uv run pytest -q -- all run after `git rm experiments/archive/test_all_improvements.py experiments/archive/test_djen_api.py`"
summary: "ruff check: 'All checks passed!'. ruff format --check: '378 files already formatted'. pytest -q: exit code 0, 1463 passed (dot count), 1 skipped, 0 failed/errored -- identical outcome to the pre-deletion baseline, confirming the deletion is a true no-op for every automated gate (both files were already excluded from pytest collection by testpaths=[\"tests\"] in pyproject.toml, and were never imported by any collected test or source module) rather than a hidden regression."
---

# Evidência GREEN — suíte completa após a remoção

`ruff check`, `ruff format --check` e `pytest -q` completos permanecem limpos depois de remover os dois arquivos órfãos, confirmando que a exclusão não tinha efeito colateral em nenhum gate automatizado.
