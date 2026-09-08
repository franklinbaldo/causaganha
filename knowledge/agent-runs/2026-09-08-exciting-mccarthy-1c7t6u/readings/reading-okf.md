---
type: AgentReading
id: "2026-09-08-exciting-mccarthy-1c7t6u-reading-okf"
subject: "knowledge OKF bundle"
run_id: "2026-09-08-exciting-mccarthy-1c7t6u"
---

# Reading: knowledge OKF bundle

Read `knowledge/index.md` and surveyed `knowledge/{backlog,contracts,pipelines,projections,sources}/`. The bundle models: 4 product data sources (`datajud`, `djen`, `stj-acordaos`, `tjro-juris`) each with a matching pipeline document (natural-key `fonte` linking pipeline → source), 8 data contracts (`processo`, `processo-ausente`, `djen-resumo`, `datajud-capa`, `documento-processo`, `fonte-cobertura`, `juris-decisao`, `stj-acordao`), 1 projection (`processo-consultar`), and 18 backlog docs mirroring the open GitHub issues 1:1. This layer is explicitly the product's knowledge/contracts plane, separate from the Parquet/DuckDB data plane.

Also read the most recent same-family completed `AgentRun` report (`knowledge/agent-runs/2026-09-08-exciting-mccarthy-obl3ux/run.md`) for continuity: it fixed a weekend/calendar-day completion-metric bug (PR #1313, merged) and left two next-move leads. Per the PR reading above, both leads were independently resolved by a separate round family since then (#1332, #1330), so this round cannot resume them and needs fresh work.

Ran `uv run okf-parser check knowledge --relational-schema okf.schema.sql` as the baseline check: `conformant: true`, 0 diagnostics, 782 concepts, 785 markdown files, 3 reserved. See `checks/check-okf-parser-baseline.md`.
