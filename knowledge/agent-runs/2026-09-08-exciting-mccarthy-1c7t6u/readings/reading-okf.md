---
type: AgentReading
id: "2026-09-08-exciting-mccarthy-1c7t6u-reading-okf"
run_id: "2026-09-08-exciting-mccarthy-1c7t6u"
subject: "okf_knowledge"
reference: "knowledge/index.md; knowledge/{backlog,contracts,pipelines,projections,sources}/; knowledge/agent-runs/2026-09-08-exciting-mccarthy-obl3ux/run.md"
finding: "The bundle models 4 product data sources (datajud, djen, stj-acordaos, tjro-juris) each with a matching pipeline document, 8 data contracts (processo, processo-ausente, djen-resumo, datajud-capa, documento-processo, fonte-cobertura, juris-decisao, stj-acordao), 1 projection (processo-consultar), and 18 backlog docs mirroring the open GitHub issues 1:1. Read the most recent same-family completed AgentRun report (obl3ux) for continuity: it fixed a weekend/calendar-day completion-metric bug (PR #1313, merged) and left two next-move leads. Per the PR reading, both leads were independently resolved by a separate round family since then, so this round needed fresh work. Ran uv run okf-parser check knowledge --relational-schema okf.schema.sql as the baseline check: conformant, 0 diagnostics, 782 concepts."
---

# Reading: knowledge OKF bundle

Levantamento da estrutura do bundle (sources/pipelines/contracts/projections/backlog) e leitura do relatório mais recente da mesma família (`obl3ux`) para continuidade. Check `okf-parser` baseline: conformante, 782 conceitos, 0 diagnósticos.
