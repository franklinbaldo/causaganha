---
type: "RunCheck"
id: "run-checks/20260914t172602z-do-the-best-useful-work-availab/check-verification"
run: "runs/20260914T172602Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest tests/test_pilot_tjro_2026_query_cost.py -q; uv run pytest -q (full repo suite); uv run ruff check; uv run ruff format --check"
result: "12/12 new tests green (row-group-pruning proxy against synthetic sorted/scattered fixtures; local Range-HTTP server byte-range/query-string/reset/stats correctness, including a real thread-timing race fixed by recording stats before flushing the response body). Full repo suite (uv run pytest -q, no path filter) passed with 0 failures, 1 skip (pre-existing, unrelated). uv run ruff check and uv run ruff format --check both report clean across the whole repo. The end-to-end benchmark itself was independently run against the real published djen-tjro-2026/comunicacoes.parquet (not a mock), producing docs/planning/evidence/pilot-tjro-2026-query-cost.json."
status: "pass"
evidence: "run-evidence/20260914t172602z-do-the-best-useful-work-availab/evidence-query-cost-benchmark"
goal: "run-goals/20260914t172602z-do-the-best-useful-work-availab/goal-measure-query-cost"
---

# RunCheck
