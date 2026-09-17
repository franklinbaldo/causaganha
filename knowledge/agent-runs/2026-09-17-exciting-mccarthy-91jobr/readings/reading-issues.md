---
type: AgentReading
id: "2026-09-17-exciting-mccarthy-91jobr-reading-issues"
run_id: "2026-09-17-exciting-mccarthy-91jobr"
subject: "open_issues"
reference: "github issues (list_issues, state=OPEN, franklinbaldo/causaganha), 22 total"
finding: "#1050 segue a linhagem mais ativa do repositorio, agora dominada pelo runtime Wisk (18 lotes reais ja mesclados, document_count=149, val/test ceiling=22/22 ao vivo), ainda abaixo do piso RFC 0012 Sec 5 item 4 (>=30/>=30). Uma corrida concorrente entre esta linhagem AgentRun e o Wisk produziu duas PRs simultaneas reivindicando o 'decimo oitavo lote' (#1576 e #1577); #1577 (Wisk) mesclou primeiro, deixando #1576 (AgentRun, sessao anterior 726qh5) organicamente stale mas com 6 documentos reais e ja anotados que nao devem ser descartados."
---

# Leitura: issues abertas

`mcp__github__list_issues` (owner=franklinbaldo, repo=causaganha,
state=OPEN, orderBy=UPDATED_AT desc) retornou 22 issues. Mais relevantes:

- **#1050** ("segmenter: repair and scale the real training corpus with
  agent annotation") -- linhagem mais ativa. 18 lotes reais ja mesclados
  em `main` (ultimo: PR #1577, commit `0a831be`, via Wisk).
  `document_count=149`, `val_ceiling=test_ceiling=22` (confirmado ao vivo
  via `scripts/segmenter_governance_status.py`), ainda abaixo do piso RFC
  0012 Sec 5 item 4 (>=30 val, >=30 test) -- `corpus_scale_blocks_floor:
  true`.
- **#1051** ("segmenter: build an independently annotated validation
  set") -- bloqueada estruturalmente ate #1050 crescer o corpus total.
- **#1482** (CORS em archive.org para `DuckDBExplorer.read_parquet()`)
  -- aberta; PR #1576 (nao mesclada) documenta que o workaround de codigo
  e a prova de CI ja foram mesclados em rodada anterior, restando apenas
  o deploy real do Cloudflare Worker, bloqueado por credenciais que este
  ambiente nao tem. Nao acionavel nesta rodada.
- **#1468-#1472** (cadeia Parquet/CNJ) -- linhagem paralela, parte
  bloqueada por credenciais IA ausentes, fora do controle desta sessao.
- **#950/#951** (endpoint MCP publico read-only) -- sem rodada dedicada
  recente; candidata a trabalho futuro caso a linhagem #1050 sature.

Achado operacional novo desta rodada (nao presente nas leituras
anteriores): `list_pull_requests` mostra **duas PRs abertas
simultaneamente reivindicando o "decimo oitavo lote"** de #1050 -- #1576
(este mecanismo AgentRun, sessao `726qh5`, 6 documentos:
TJMT/74430633, TJRR/568209392, TJRR/568328945, TRF3/42490599,
TRF5/349186353, TRF5/463264301) e #1577 (Wisk, ja mesclado como
`0a831be`, 6 documentos diferentes: TJES/577030718, TJES/577039281,
TJRR/568111547, TJRR/568208030, TJMT/74428001, TRF3/42490548). Nenhum
documento se sobrepoe entre as duas PRs -- ambas fizeram trabalho real e
distinto, mas a corrida de numeracao ("lote 18" duas vezes) e o fato de
`main` ja ter avancado tornam #1576 organicamente stale (evidencia de
audit em `docs/planning/evidence/segmenter-djen-sample-batch18-*.json`
colide de nome com o que Wisk ja commitou). Isso e o proprio conflito
AgentRun-vs-Wisk (ja mapeado desde 2026-09-14) se materializando como
custo concreto pela primeira vez, nao apenas teorico.
