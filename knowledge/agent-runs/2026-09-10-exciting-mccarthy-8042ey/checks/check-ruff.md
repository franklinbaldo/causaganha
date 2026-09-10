---
type: AgentCheck
id: "2026-09-10-exciting-mccarthy-8042ey-check-ruff"
run_id: "2026-09-10-exciting-mccarthy-8042ey"
goal_id: "2026-09-10-exciting-mccarthy-8042ey-goal-writeback-constants-drift"
command: "uv run ruff check scripts/render_manifest_parquet.py tests/test_render_manifest_writeback.py && uv run ruff format --check scripts/render_manifest_parquet.py tests/test_render_manifest_writeback.py"
result: "passed"
evidence_id: "2026-09-10-exciting-mccarthy-8042ey-evidence-diff"
summary: "All checks passed! / 2 files already formatted."
---

# Check ruff

Lint e formatação limpos nos arquivos alterados.
