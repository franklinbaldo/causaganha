---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-ko7vqq-check-ruff"
run_id: "2026-09-09-exciting-mccarthy-ko7vqq"
command: "uv run ruff check && uv run ruff format --check"
result: "passed"
summary: "`ruff check`: All checks passed! `ruff format --check`: 405 files already formatted. Run after the DataJud fix."
---

# Check: ruff check + format

Ambos limpos após a correção do DataJud.
