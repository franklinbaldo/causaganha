---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-tp38w3-check-python-checks-unaffected"
run_id: "2026-09-06-exciting-mccarthy-tp38w3"
goal_id: "2026-09-06-exciting-mccarthy-tp38w3-goal-mostrar-mudancas-desde-ultima-consulta"
command: "uv run ruff check && uv run ruff format --check && uv run pytest -q"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-tp38w3-evidence-full-suite-and-static-checks-green"
summary: "ruff check: All checks passed. ruff format --check: 378 files already formatted. pytest -q: no F/E outcomes (1456 '.' + 1 's', counted directly since this repo's pytest config prints no final summary line) — confirms zero Python regression from this round's web-only change."
---

# Check: gates Python (`uv run ruff check`, `ruff format --check`, `pytest -q`)
