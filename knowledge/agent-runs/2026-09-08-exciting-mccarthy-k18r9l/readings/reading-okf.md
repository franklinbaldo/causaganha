---
type: AgentReading
id: "2026-09-08-exciting-mccarthy-k18r9l-reading-okf"
run_id: "2026-09-08-exciting-mccarthy-k18r9l"
subject: "okf_knowledge"
reference: "knowledge/index.md; knowledge/{backlog,contracts,pipelines,projections,sources}/; knowledge/agent-runs/2026-09-08-exciting-mccarthy-b4t8pv/run.md; uv run okf-parser check knowledge --relational-schema okf.schema.sql"
finding: "Bundle shape unchanged from the last several rounds: 4 sources (datajud, djen, stj-acordaos, tjro-juris), 4 pipelines, 8 contracts, 1 projection (processo-consultar), 18 backlog docs mirroring the 17 open GitHub issues plus one archived entry. Read the most recent completed same-family AgentRun (b4t8pv) for continuity: it fixed totals.qmd/tribunal_coverage.qmd's pending-bucket undercount for djen_status='confirmed' rows (merged PR #1338), and left three low/no-TDD-shape leads plus one new lead (court_reliability.qmd/tribunal_calendar.qmd lack test coverage for a confirmed row, though their own frontmatter documents they're intentionally restricted to uploaded/absent) -- none of the three carried-over leads were picked up since. Baseline check run before any new content this round: `uv run okf-parser check knowledge --relational-schema okf.schema.sql` -> conformant, 815 concepts, 818 markdown files, 3 reserved, 0 diagnostics (up from b4t8pv's own final count of 814, reflecting the one docs-closing commit for that PR plus PR #1342's own in-flight run report from the parallel session)."
---

# Reading: knowledge OKF bundle

Estrutura do bundle inalterada (4 sources, 4 pipelines, 8 contracts, 1 projection, 18 backlog). Relatório mais recente da mesma família (`b4t8pv`) lido para continuidade. Check baseline: conformante, 815 conceitos, 0 diagnósticos.
