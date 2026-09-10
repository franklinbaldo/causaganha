---
type: AgentCheck
id: "2026-09-10-exciting-mccarthy-41w39p-check-ruff"
run_id: "2026-09-10-exciting-mccarthy-41w39p"
goal_id: "2026-09-10-exciting-mccarthy-41w39p-goal-background-upload-not-orphaned"
command: "uv run ruff check src/djen_backup/engine.py tests/djen_backup/test_background_manifest_upload.py && uv run ruff format --check src/djen_backup/engine.py tests/djen_backup/test_background_manifest_upload.py"
result: "passed"
summary: "ruff check: All checks passed! ruff format --check: 2 files already formatted."
---

# Check: ruff

`uv run ruff check` e `uv run ruff format --check` limpos nos arquivos tocados.
