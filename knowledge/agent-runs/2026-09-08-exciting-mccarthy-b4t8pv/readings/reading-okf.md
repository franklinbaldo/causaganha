---
type: AgentReading
id: "2026-09-08-exciting-mccarthy-b4t8pv-reading-okf"
run_id: "2026-09-08-exciting-mccarthy-b4t8pv"
subject: "okf_knowledge"
reference: "knowledge/index.md; knowledge/{backlog,contracts,pipelines,projections,sources}/; knowledge/agent-runs/2026-09-08-exciting-mccarthy-1c7t6u/run.md"
finding: "The bundle models 4 product data sources (datajud, djen, stj-acordaos, tjro-juris) each with a matching pipeline document, 8 data contracts (processo, processo-ausente, djen-resumo, datajud-capa, documento-processo, fonte-cobertura, juris-decisao, stj-acordao), 1 projection (processo-consultar), and 18 backlog docs mirroring the 17 open GitHub issues (plus one closed/archived entry). Read the most recent same-family completed AgentRun report (1c7t6u) for continuity: it fixed consolidation_status.qmd's hardcoded 90-tribunal threshold (PR #1336, merged) and left three next-move leads (except-Exception/BLE001 policy gap, README optional-contracts staleness, unverified consolidation_status.qmd prose vs. ia_status semantics) -- none picked up since, per this round's PR reading. Ran uv run okf-parser check knowledge --relational-schema okf.schema.sql as the round's baseline check before any new content was added: conformant, 0 diagnostics, 798 concepts, 801 markdown files, 3 reserved -- matches the count implied by 1c7t6u's own final check (797) plus the one docs-closing commit (#1337) since then."
---

# Reading: knowledge OKF bundle

Levantamento da estrutura do bundle (sources/pipelines/contracts/projections/backlog) e leitura do relatório mais recente da mesma família (`1c7t6u`) para continuidade. Check `okf-parser` baseline (antes de qualquer conteúdo novo desta rodada): conformante, 798 conceitos, 0 diagnósticos.
