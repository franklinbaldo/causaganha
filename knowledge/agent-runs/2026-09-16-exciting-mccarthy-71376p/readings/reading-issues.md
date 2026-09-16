---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-71376p-reading-issues"
run_id: "2026-09-16-exciting-mccarthy-71376p"
subject: "open_issues"
reference: "github list_issues state=OPEN (22 total)"
finding: "#1050 (segmenter corpus scale-up) and #1051 (independent val set) remain the top of the queue by update recency, with #1050 mid-lineage through ten concurrent batch rounds today (0iuk22 through imy2ed). Also open: #1469-1472/#1468 (Parquet/CNJ rewrite work), #1482 (DuckDB/archive.org CORS), #950/#951 (MCP remote endpoint), #1022/#985 (TCU/TSE Parquet publication), #1093 (teor search UX), #1057/#1056/#1055/#1054/#1053/#1047 (segmenter experiment backlog), #884/#887/#886 (locked holdout backlog). None of these compete with the reconciliation work chosen this round (fixing PR #1559's merge conflict against #1050's own lineage)."
---

# Leitura: issues abertas

22 issues abertas no total. `#1050` é a issue mais ativa (atualizada há
minutos, pela rodada `imy2ed`/PR #1559), seguida por `#1051` (bloqueada
estruturalmente pelo tamanho do corpus, conforme
`scripts/segmenter_governance_status.py` já confirma há várias rodadas:
`corpus_scale_blocks_floor=true`). O resto da fila (Parquet/CNJ, CORS do
DuckDB, MCP remoto, TCU/TSE, UX de busca de teor, backlog de experimentos
do segmentador) segue sem trabalho reivindicado nesta janela — nenhuma
delas foi escolhida porque a PR #1559, já aberta e com conflito de merge
real contra `main`, é o avanço de maior alavancagem imediata: sem
resolvê-la, um lote 11 duplicaria esforço em vez de destravar o que já
está pronto.
