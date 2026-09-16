---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-5lvbii-reading-issues"
run_id: "2026-09-16-exciting-mccarthy-5lvbii"
subject: "open_issues"
reference: "github:franklinbaldo/causaganha issues state=OPEN (22 total)"
finding: "#1050 (segmenter: repair and scale the real training corpus with agent annotation) and #1051 (segmenter: build an independently annotated validation set) are the active lineage: 11 real multi-tribunal batches already merged as PRs (#1537-#1562, the last still open) via the proven scripts/ingest_djen_sample_technique1_batch.py mechanism; #1051 stays blocked by RFC 0012 Sec 5 item 4's per-split floor (val/test ceiling tracks total document_count, confirmed stuck at the same value across the last several batches until document_count crosses further steps). #1470-1472/#1468-1469 (Parquet/CNJ reorder+read-back pilot) remain blocked in every environment checked back to 2026-09-11: no IA_ACCESS_KEY/IA_SECRET_KEY in env (re-confirmed live this round, `env | grep -i IA_` empty). #1482 (DuckDB-WASM CORS block on archive.org download endpoint) has a real fix committed (PR #1521, Cloudflare Worker proxy) but stays open because deploying the Worker needs Cloudflare credentials this session also lacks -- same class of blocker as the IA credentials gap. No other open issue (#1093, #1057/1056/1055/1054/1053, #1047, #1022, #985, #951/950, #887/886/884) has fresh activity today; they are pre-existing backlog, not something a prior round left mid-flight."
---

# Leitura: issues abertas

Linhagem ativa é #1050/#1051 (segmentador, RFC 0012) -- 11 lotes reais já
mesclados, mecanismo provado. #1051 continua travado pelo piso por-split
(RFC 0012 Sec 5 item 4) até o corpus crescer mais. #1470-1472/#1468-1469
(reorder Parquet/CNJ) e #1482 (CORS DuckDB-WASM) têm trabalho pronto mas
travado por credenciais ausentes neste ambiente (IA e Cloudflare,
respectivamente), reconfirmado ao vivo. Nenhuma outra issue aberta tem
atividade recente que indique trabalho interrompido a retomar.
