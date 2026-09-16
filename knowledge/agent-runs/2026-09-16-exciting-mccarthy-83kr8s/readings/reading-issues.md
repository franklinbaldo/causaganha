---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-83kr8s-reading-issues"
run_id: "2026-09-16-exciting-mccarthy-83kr8s"
subject: "open_issues"
reference: "GitHub issues list (state=OPEN, 22 total, first page ordered by updated_at desc): #1050, #1051, #1469, #1482, #1470, #1471, #1472, #1468, #950, #1022, #985, #951, #1093, #1057, #1056, #1055, #1054, #1047, #1053, #884, plus 2 more not fetched"
finding: "#1050 (segmenter: repair and scale the real training corpus with agent annotation) remains the most recently updated issue and the direct continuation point: six prior real batches this same day (61->68->74->81->86->93 documents, val/test ceiling 9->10->11->12->13->14) all used scripts/ingest_djen_sample_technique1_batch.py and left next_move asking for more batches. The immediately prior round (la7bsl, merged PR #1547/#1548) confirmed tribunal-diversity mining is exhausted (25 tribunals represented, a live scan of the full sample pool under a widened 2500-char floor found no brand-new tribunal beyond the 25 already covered) and explicitly redirected the next round to keep drawing additional Sentença/Acórdão candidates from already-represented tribunals -- document_count growth, not tribunal diversity, is what raises the RFC 0012 Sec 5 item 4 floor from here. #1051 (independent validation set) remains correctly parked behind #1050 -- val/test ceiling is 14/14 against a >=30/>=30 floor, unchanged, no new fact reopens it. Parquet/CNJ epic (#1468-1472) remains blocked on missing IA_ACCESS_KEY/IA_SECRET_KEY credentials this session does not have. #1482 (DuckDB CORS on archive.org file-download) is a live, unaddressed frontend bug outside this round's selected lineage -- left for a dedicated frontend round. #950/#951/#1093/#1022/#985/#1053-1057/#1047 remain lower priority or gated on a larger segmenter corpus, unchanged."
---

# Leitura: issues abertas

22 issues abertas. #1050 continua a mais recentemente atualizada e o
ponto de continuidade direto: 6 lotes reais nesta mesma data (61->93
documentos) ja rodaram pelo mesmo mecanismo. A rodada imediatamente
anterior (la7bsl) confirmou que a diversidade de tribunal esta esgotada
(25 tribunais ja representados, nenhum tribunal novo restante mesmo com
filtro ampliado) e redirecionou explicitamente para continuar extraindo
candidatos Sentenca/Acordao de tribunais ja representados. #1051
permanece corretamente atras de #1050. Epic Parquet/CNJ (#1468-1472)
permanece bloqueado por credenciais IA ausentes. #1482 e um bug real de
frontend fora da linhagem selecionada, deixado para rodada dedicada.
Demais issues sem mudanca relevante.
