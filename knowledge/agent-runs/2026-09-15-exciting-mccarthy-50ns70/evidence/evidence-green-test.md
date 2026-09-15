---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-50ns70-evidence-green-test"
run_id: "2026-09-15-exciting-mccarthy-50ns70"
goal_id: "2026-09-15-exciting-mccarthy-50ns70-goal-cors-probe-ci"
kind: "test_green"
reference: "scripts/benchmarks/archive_cors_probe.py, tests/test_archive_cors_probe.py"
summary: "Restored scripts/benchmarks/archive_cors_probe.py (evaluate_cors_probe_result, FetchOutcome, CorsProbeResult, Verdict, run_probe, main). `uv run pytest tests/test_archive_cors_probe.py -q` -> 4 passed. `uv run ruff check` and `uv run ruff format --check` on both files -> clean. Full repo `uv run ruff check` / `ruff format --check` (all files) -> clean."
---

# Evidência: teste GREEN

`uv run pytest tests/test_archive_cors_probe.py -q`: 4 passed. `uv run ruff check` / `ruff format --check`: sem problemas nos arquivos novos e no repositório inteiro.
