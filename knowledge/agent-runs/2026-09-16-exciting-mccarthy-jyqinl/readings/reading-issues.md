---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-jyqinl-reading-issues"
run_id: "2026-09-16-exciting-mccarthy-jyqinl"
subject: "open_issues"
reference: "GitHub issues list (state=OPEN, 22 total, ordered by updated_at desc): #1050, #1051, #1469, #1482, #1470, #1471, #1472, #1468, #950, #1022, #985, #951, #1093, #1057, #1056, #1055, #1054, #1047, #1053, #884, #887, #886"
finding: "#1050 (segmenter: repair and scale the real training corpus with agent annotation) is the most recently updated issue and is the direct continuation point: its knowledge/backlog/issue-1050.md (status=unblocked) explicitly says a future round should 'run more batches through scripts/ingest_djen_sample_technique1_batch.py (data/segmenter_samples/*.jsonl still holds ~820 unused real candidates across ~30 tribunals)'. #1051 (independently annotated validation set) remains correctly redirected behind #1050 by 2 prior rounds' live proof that adjudicating the existing pool cannot cross the RFC 0012 Sec 5 item 4 per-split floor -- not touched again until the corpus is bigger. The Parquet/CNJ epic (#1468-1472) remains blocked on missing IA_ACCESS_KEY/IA_SECRET_KEY (unchanged since 2026-09-11, reconfirmed by every round since). #1482 (DuckDB CORS on archive.org file-download endpoint) is a live, unaddressed frontend bug but outside this round's selected lineage. #950/#951/#1093/#1022/#985 (MCP endpoint, TCU/TSE datasets, direct decision search) and #1053-1057/#1047 (later-stage segmenter training/active-learning work, all explicitly gated on a bigger corpus existing first) remain lower priority or blocked-by-corpus-size, unchanged. #884/#886/#887 are the sibling locked-holdout lineage, explicitly out of scope for #1050's train-supply work (confirmed again this round: no overlap in candidate sources used)."
---

# Leitura: issues abertas

`list_issues` (state=OPEN) retornou 22 issues, mesma lista das rodadas
anteriores. #1050 continua a mais recentemente atualizada e o proprio
`knowledge/backlog/issue-1050.md` (preenchido pela rodada anterior,
0iuk22) pede explicitamente mais lotes pelo mesmo mecanismo de ingestao,
citando os ~820 candidatos reais ainda nao usados em
`data/segmenter_samples/*.jsonl`. #1051 permanece corretamente atras de
#1050 (nao ha razao nova para revisitar a adjudicacao do pool antigo).
Epic Parquet/CNJ (#1468-1472) permanece bloqueado por credenciais IA
ausentes, inalterado. Demais issues (#1482 CORS DuckDB, #950/#951 MCP,
#1022/#985 datasets, #1053-1057/#1047 treino/active-learning do
segmentador) permanecem de prioridade menor ou explicitamente dependentes
de um corpus maior existir primeiro -- nenhuma mudanca de estado desde a
ultima rodada que as avaliou.
