---
goal: "Measure DuckDB native + WASM date-only (no CNJ) query cost for issue #1471's TJRO 2026 pilot, comparing the currently published djen-tjro-2026/comunicacoes.parquet against the numero_processo-first candidate rewrite, separating engine init/cold query/warm cache and recording bytes/requests/duration/sample/environment."
id: "run-goals/20260914t172602z-do-the-best-useful-work-availab/goal-measure-query-cost"
kind: "task-advance"
rationale: "Two of issue #1471's acceptance criteria ('Medir consultas por data sem CNJ' and 'Usar DuckDB nativo e WASM; separar inicialização do motor, consulta fria e cache quente') are still open after PR #1478's local-diff-only slice, and handoffs/handoff-issue-1471-perf-and-readback names this measurement as the next concrete step before any Archive publish or rollout decision."
run: "runs/20260914T172602Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "A JSON evidence file quantifies, for both engines and both files, per-phase duration/requests/bytes plus the row-group-pruning proxy metric; new unit tests (tests/test_pilot_tjro_2026_query_cost.py) pass; full repo suite and ruff stay green."
type: "RunGoal"
---

# RunGoal
