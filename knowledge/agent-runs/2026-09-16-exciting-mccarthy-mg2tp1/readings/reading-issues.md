---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-mg2tp1-reading-issues"
run_id: "2026-09-16-exciting-mccarthy-mg2tp1"
subject: "open_issues"
reference: "GitHub issues list (state=OPEN, 22 total, ordered by updated_at desc): #1050, #1051, #1469, #1482, #1470, #1471, #1472, #1468, #950, #1022, #985, #951, #1093, #1057, #1056, #1055, #1054, #1047, #1053, #884, #887, #886"
finding: "#1050 (segmenter: repair and scale the real training corpus with agent annotation) remains the most recently updated issue and the direct continuation point. knowledge/backlog/issue-1050.md (status=unblocked, last_verified_run_id=2026-09-16-exciting-mccarthy-uyx7xc) documents three completed real batches (61->68->74->81 documents, val/test ceiling 9->10->11->12) and asks the next round to keep running batches through scripts/ingest_djen_sample_technique1_batch.py, checking each candidate's raw texto_limpo for XML-parseability (ET.fromstring on <text>...</text>) before assigning it to a subagent and running the batch3 HTML-to-plain-text cleaner when it doesn't parse. #1051 (independent validation set) remains correctly parked behind #1050: three prior rounds proved live that adjudicating the existing pool cannot cross RFC 0012 Sec 5 item 4's per-split floor (needs corpus size, not more adjudication of a fixed pool) -- no new fact reopens that. Parquet/CNJ epic (#1468-1472) remains blocked on missing IA_ACCESS_KEY/IA_SECRET_KEY credentials this session does not have. #1482 (DuckDB CORS on archive.org file-download) is a live, unaddressed frontend bug outside this round's selected lineage -- no new information changes that triage. #950/#951/#1093/#1022/#985 and #1053-1057/#1047 remain lower priority or explicitly gated on a bigger segmenter corpus existing first, unchanged."
---

# Leitura: issues abertas

22 issues abertas, mesma lista das rodadas recentes. #1050 continua a
mais recentemente atualizada, com `knowledge/backlog/issue-1050.md`
pedindo explicitamente mais lotes pelo mesmo mecanismo de ingestao,
agora com o cuidado adicional de checar a parseabilidade XML do texto
bruto antes de anotar. #1051 permanece corretamente atras de #1050.
Epic Parquet/CNJ (#1468-1472) permanece bloqueado por credenciais IA
ausentes nesta sessao. Demais issues sem mudanca de estado relevante
para esta rodada.
