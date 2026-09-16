---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-zrek2s-reading-issues"
run_id: "2026-09-16-exciting-mccarthy-zrek2s"
subject: "open_issues"
reference: "github issues (list_issues, state=OPEN, franklinbaldo/causaganha)"
finding: "22 issues abertas. #1050 (segmenter: repair and scale the real training corpus) e #1051 (segmenter: build an independently annotated validation set) sao a linhagem mais ativa -- 6 rodadas consecutivas hoje (0iuk22, c4y4rc, jyqinl, uyx7xc, mg2tp1, la7bsl + uma rodada Wisk) ja entregaram 6 lotes reais mesclados, todos avancando document_count sem tocar codigo de producao. Outra linhagem paralela e a cadeia Parquet/CNJ (#1468-#1472), conduzida por rodadas Wisk ('docs(wisk)'), com #1471 bloqueada continuamente ha 9+ rodadas por falta de credenciais IA_ACCESS_KEY/IA_SECRET_KEY (fora do meu controle). #1482 (CORS em archive.org para DuckDBExplorer) e nova (atualizada 2026-09-15) e nao tem nenhuma rodada dedicada ainda. Issues #1053-#1057, #884, #886-#887 sao trabalho de segmentador de fases futuras (treino de modelo, active learning) que dependem do piso de corpus de #1050/#1051 ainda nao atingido."
---

# Leitura: issues abertas

`mcp__github__list_issues` (owner=franklinbaldo, repo=causaganha,
state=OPEN, orderBy=UPDATED_AT desc) retornou 22 issues. As mais
relevantes para continuidade:

- **#1050** ("segmenter: repair and scale the real training corpus with
  agent annotation") -- linhagem ativa ha 6+ rodadas hoje, mecanismo
  `scripts/ingest_djen_sample_technique1_batch.py` ja provado em 6 lotes
  reais mesclados (document_count 61->96 confirmado ao vivo via
  `scripts/segmenter_governance_status.py`, val/test ceiling ainda em
  14/14 contra o piso >=30/>=30 de RFC 0012 Sec 5 item 4).
- **#1051** ("segmenter: build an independently annotated validation
  set") -- bloqueada estruturalmente enquanto #1050 nao levantar o teto
  val/test acima de 30 (confirmado matematicamente por rodadas
  anteriores: adjudicar mais do pool atual nao cruza o teto).
- **#1468-#1472** (cadeia Parquet/CNJ) -- conduzida por rodadas Wisk
  paralelas; #1471 (validar piloto TJRO 2026) bloqueada ha 9+ rodadas por
  falta de credenciais IA, fora do meu controle nesta sessao.
- **#1482** (CORS em archive.org para DuckDBExplorer.read_parquet()) --
  aberta, sem rodada dedicada ainda; candidata a trabalho futuro se a
  linhagem #1050 saturar ou bloquear.
- **#1053-#1057, #884, #886-#887** -- fases futuras do segmentador
  (treino de modelo real, active learning, benchmarks) que dependem do
  corpus de #1050/#1051 atingir o piso RFC 0012; nao acionaveis ainda.

Nenhuma issue aberta hoje sugere que a linhagem #1050 deva ser
abandonada; ao contrario, o proprio numero de rodadas consecutivas bem
sucedidas e o sinal mais forte de continuidade disponivel.
