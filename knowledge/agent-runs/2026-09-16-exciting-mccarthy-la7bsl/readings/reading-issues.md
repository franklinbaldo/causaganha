---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-la7bsl-reading-issues"
run_id: "2026-09-16-exciting-mccarthy-la7bsl"
subject: "open_issues"
reference: "GitHub issues list (state=OPEN, 22 total, ordered by updated_at desc): #1050, #1051, #1469, #1482, #1470, #1471, #1472, #1468, #950, #1022, #985, #951, #1093, #1057, #1056, #1055, #1054, #1047, #1053, #884, plus 2 more not fetched in this page"
finding: "#1050 (segmenter: repair and scale the real training corpus with agent annotation) remains the most recently updated issue and the direct continuation point: five prior real batches this same day (61->68->74->81->86 documents, val/test ceiling 9->10->11->12->13) all used scripts/ingest_djen_sample_technique1_batch.py and left next_move asking for more batches. The immediately prior round (mg2tp1, merged PR #1545/#1546) found tribunal diversity nearly exhausted in the sample pool under its 4000-17000 char filter (only 8 tribunals left without a usable candidate: STM, TJAC, TJAM, TJAP, TJMS, TJPE, TJSP, TRF1) and explicitly redirected the next round to widen candidate selection to Sentença/Acórdão documents in already-represented tribunals instead of chasing new-tribunal diversity. #1051 (independent validation set) remains correctly parked behind #1050: RFC 0012 Sec 5 item 4's per-split floor (>=30 val, >=30 test) cannot be reached by adjudicating the fixed pool, only by growing document_count -- unchanged, no new fact reopens it. Parquet/CNJ epic (#1468-1472) remains blocked on missing IA_ACCESS_KEY/IA_SECRET_KEY credentials this session does not have. #1482 (DuckDB CORS on archive.org file-download) is a live, unaddressed frontend bug outside this round's selected lineage -- left for a dedicated frontend round. #950/#951/#1093/#1022/#985/#1053-1057/#1047 remain lower priority or gated on a larger segmenter corpus, unchanged."
---

# Leitura: issues abertas

22 issues abertas. #1050 continua a mais recentemente atualizada e o
ponto de continuidade direto: 5 lotes reais nesta mesma data (61->86
documentos) ja rodaram pelo mesmo mecanismo. A rodada imediatamente
anterior (mg2tp1) esgotou quase toda a diversidade de tribunal nova sob
seu filtro de 4000-17000 caracteres e redirecionou explicitamente para
ampliar a selecao a candidatos Sentenca/Acordao em tribunais ja
representados. #1051 permanece corretamente atras de #1050. Epic
Parquet/CNJ (#1468-1472) permanece bloqueado por credenciais IA
ausentes. #1482 e um bug real de frontend fora da linhagem selecionada,
deixado para rodada dedicada. Demais issues sem mudanca relevante.
