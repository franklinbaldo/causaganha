---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-6tcxrn-check-1178-ruff-pytest"
run_id: "2026-09-06-exciting-mccarthy-6tcxrn"
goal_id: "2026-09-06-exciting-mccarthy-6tcxrn-goal-1178-single-theme-decision"
command: "uv run ruff check && uv run ruff format --check && uv run pytest -q"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-6tcxrn-evidence-1178-full-gates-green"
summary: "ruff check: all checks passed. ruff format --check: 378 files already formatted. pytest -q: full suite green (1 skipped, rest passed). Required by CLAUDE.md's 'Before committing' section even though this round's diff is web/-only, since the OKF report itself lives under knowledge/ and is checked by the same gates."
---

# Check — gates Python padrão do CLAUDE.md
