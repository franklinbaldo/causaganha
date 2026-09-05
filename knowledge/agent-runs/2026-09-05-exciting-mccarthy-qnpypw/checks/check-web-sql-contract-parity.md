---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-qnpypw-check-web-sql-contract-parity"
run_id: "2026-09-05-exciting-mccarthy-qnpypw"
goal_id: "2026-09-05-exciting-mccarthy-qnpypw-goal-close-1042-catalog-parity-proof"
command: "uv run python: DuckDB execution of the literal SQL strings from web/src/lib/processoCnj.ts (buildIndiceSql/buildDjenSql/buildJurisSql/buildDatajudSql) against the same published parquets, for the same CNJ; also attempted playwright (python) navigation to https://franklinbaldo.github.io/causaganha/processo?cnj=... which failed with net::ERR_CONNECTION_RESET"
result: "passed"
evidence_id: "2026-09-05-exciting-mccarthy-qnpypw-evidence-web-sql-contract-parity"
summary: "SQL-contract execution produced results identical field-for-field to processo_consultar's output. The browser-render attempt failed due to a confirmed environment-wide proxy limitation (curl to $HTTPS_PROXY/__agentproxy/status showed systemic ws_closed_mid_exchange failures to unrelated hosts too), not a defect in the product; documented and worked around via the SQL-contract method instead."
---

# Check: paridade de contrato SQL web × MCP
