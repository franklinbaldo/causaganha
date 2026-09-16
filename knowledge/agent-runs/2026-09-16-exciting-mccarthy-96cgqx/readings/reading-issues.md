---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-96cgqx-reading-issues"
run_id: "2026-09-16-exciting-mccarthy-96cgqx"
subject: "open_issues"
reference: "github issues (list_issues, state=OPEN, franklinbaldo/causaganha, orderBy=UPDATED_AT desc, perPage=30)"
finding: "22 issues abertas. #1050/#1051 permanecem a linhagem mais ativa e mais tratavel: doze lotes reais ja mesclados hoje (document_count 61->121, val_ceiling/test_ceiling ainda 18/18 contra o piso >=30/>=30 de RFC 0012 Sec 5 item 4 -- verificado ao vivo via scripts/segmenter_governance_status.py). Explorei tambem #1482 (CORS archive.org/DuckDBExplorer) e a cadeia Parquet/CNJ #1468-1472: #1482 ja tem toda a mitigacao de aplicacao implementada e testada (resolveArchiveDownloadBase, classificacao de erro CORS na UI, worker Cloudflare deployment/archive-cors-proxy com testes e CI proprio) -- o unico item que falta e um deploy real do Worker com credenciais Cloudflare, que esta sessao nao possui e que e uma acao de infraestrutura de producao fora do que devo executar sem confirmacao humana; a cadeia Parquet/CNJ (#1468-1472) e um epico de risco alto (regeneracao de Parquet publicado, comparacao antes/depois, prova de leitura real no Archive) que rodadas anteriores (Wisk) relatam bloqueado por falta de credenciais IA_ACCESS_KEY/IA_SECRET_KEY, fora do meu controle. Por eliminacao e por ser a via de avanco real, segura e inteiramente testável localmente, #1050 e a escolha desta rodada -- 13o lote da linhagem."
---

# Leitura: issues abertas

`mcp__github__list_issues` (owner=franklinbaldo, repo=causaganha,
state=OPEN, orderBy=UPDATED_AT desc, perPage=30) retornou 22 issues.

- **#1050** ("segmenter: repair and scale the real training corpus with
  agent annotation") -- doze lotes reais mesclados hoje (0iuk22, jyqinl,
  uyx7xc, mg2tp1, la7bsl, Wisk-lote6/PR#1549, zrek2s/PR#1553,
  83kr8s/PR#1552, hv2ep2/PR#1557, imy2ed/PR#1559, Wisk-lote11/PR#1562,
  5lvbii/PR#1563). `document_count` 61->121 (verificado ao vivo agora:
  121), `val_ceiling`/`test_ceiling` ainda em 18/18 contra o piso
  >=30/>=30 de RFC 0012 Sec 5 item 4. Mecanismo
  `scripts/ingest_djen_sample_technique1_batch.py` provado estavel em
  doze rodadas, sem mudanca de codigo de producao na maioria delas.
- **#1051** ("segmenter: build an independently annotated validation
  set") -- bloqueada estruturalmente ate o teto val/test de #1050 passar
  de 30 (confirmado matematicamente por rodadas anteriores).
- **#1482** ("CORS em archive.org bloqueia DuckDBExplorer.read_parquet()")
  -- investigada nesta rodada: `web/src/lib/archiveProxyBase.ts`,
  `DuckDBExplorer.svelte` (classificacao `cors-blocked` com mensagem
  citando #1482), `deployment/archive-cors-proxy` (Worker Cloudflare
  completo, testado, com job CI `archive-cors-proxy` verde) e
  `.github/workflows/archive-cors-probe.yml` (probe real de browser
  agendado) ja existem e cobrem toda a mitigacao de aplicacao possivel
  sem credenciais de nuvem. O deploy real do Worker (`wrangler deploy`)
  e a definicao de `PUBLIC_ARCHIVE_PROXY_BASE` no pipeline de build
  (`deploy-web.yml`) sao a unica peca faltante -- uma acao de
  infraestrutura de producao (requer `CLOUDFLARE_API_TOKEN`, que nao
  esta disponivel nesta sessao) que nao devo executar/simular sem
  confirmacao humana explicita. Nao selecionada como trabalho desta
  rodada por esse motivo.
- **#1468-#1472** (cadeia Parquet/CNJ) -- epico de alto risco
  (regeneracao de Parquet publicado, prova de leitura real no Archive),
  historicamente bloqueado por falta de credenciais IA
  (`IA_ACCESS_KEY`/`IA_SECRET_KEY`) em rodadas anteriores. Nao
  selecionada.
- **#1093** ("web(teor): busca direta de decisoes") -- o proprio corpo
  da issue declara "ESPECIFICADA, mas NAO e prioridade imediata". Nao
  selecionada.
- **#1053-#1057, #884, #886-#887** -- fases futuras do segmentador
  (treino de modelo real, active learning, benchmarks) dependentes do
  piso de corpus de #1050/#1051 ainda nao atingido. Nao acionaveis
  ainda.

Conclusao: #1050 continua sendo o unico item com avanco real,
mensuravel, seguro e inteiramente verificavel localmente disponivel
nesta rodada.
