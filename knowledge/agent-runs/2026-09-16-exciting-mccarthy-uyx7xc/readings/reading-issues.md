---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-uyx7xc-reading-issues"
run_id: "2026-09-16-exciting-mccarthy-uyx7xc"
subject: "open_issues"
reference: "GitHub issues list (state=OPEN, 22 total, ordered by updated_at desc): #1050, #1051, #1469, #1482, #1470, #1471, #1472, #1468, #950, #1022, #985, #951, #1093, #1057, #1056, #1055, #1054, #1047, #1053, #884, #887, #886"
finding: "#1050 (segmenter: repair and scale the real training corpus with agent annotation) remains the most recently updated issue and the direct continuation point. knowledge/backlog/issue-1050.md (status=unblocked, last_verified_run_id=2026-09-16-exciting-mccarthy-jyqinl) documents two completed real batches (61->68->74 documents, val/test ceiling 9->10->11) and explicitly asks the next round to run more batches through scripts/ingest_djen_sample_technique1_batch.py, now checking each candidate's texto_limpo for the '&[a-zA-Z]+;' HTML-entity pattern before assigning it to a subagent (TJTO/TJGO were dropped from batch2 after this was discovered live). #1051 (independent validation set) remains correctly parked behind #1050: two prior rounds proved live that adjudicating the existing pool cannot cross RFC 0012 Sec 5 item 4's per-split floor (needs corpus size, not more adjudication of a fixed pool) -- no new fact reopens that. Parquet/CNJ epic (#1468-1472) remains blocked on missing IA_ACCESS_KEY/IA_SECRET_KEY, unchanged since 2026-09-11. #1482 (DuckDB CORS on archive.org file-download) is a live, unaddressed frontend bug outside this round's selected lineage. #950/#951/#1093/#1022/#985 and #1053-1057/#1047 remain lower priority or explicitly gated on a bigger segmenter corpus existing first, unchanged."
---

# Leitura: issues abertas

22 issues abertas, mesma lista das rodadas recentes. #1050 continua a
mais recentemente atualizada, com `knowledge/backlog/issue-1050.md`
pedindo explicitamente mais lotes pelo mesmo mecanismo de ingestao, agora
com o cuidado adicional de checar entidades HTML antes de anotar (achado
da rodada anterior, jyqinl). #1051 permanece corretamente atras de #1050.
Epic Parquet/CNJ (#1468-1472) permanece bloqueado por credenciais IA
ausentes. Demais issues sem mudanca de estado relevante para esta rodada.
