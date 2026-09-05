---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-qnpypw-check-duckdb-intersection-discovery"
run_id: "2026-09-05-exciting-mccarthy-qnpypw"
goal_id: "2026-09-05-exciting-mccarthy-qnpypw-goal-close-1042-catalog-parity-proof"
command: "uv run python: duckdb+httpfs GROUP BY numero_processo over https://archive.org/download/causaganha-dashboard/indice_processual.parquet, filtered to rows containing djen+juris+datajud"
result: "passed"
summary: "Found exactly one CNJ (00000016620188220001) present in all three non-STJ sources, matching the reconciliation log's own reported intersection count (datajud+djen+juris=1). Used as the test case for the rest of this round's #1042 proof."
---

# Check: descoberta do CNJ multi-fonte real
