---
type: AgentReading
id: "2026-09-19-exciting-mccarthy-gbf44b-reading-issues"
run_id: "2026-09-19-exciting-mccarthy-gbf44b"
subject: "open_issues"
reference: "mcp__github__list_issues (owner=franklinbaldo, repo=causaganha, state=OPEN), 22 total"
finding: "#1050 continua a linhagem mais ativa e com caminho de execucao provado (21 lotes mesclados), mas ainda abaixo do piso RFC 0012 Sec 5 item 4 (document_count=167, val_ceiling=test_ceiling=25 confirmado ao vivo, precisa document_count>=~200). #1051 (validacao independente) permanece estruturalmente bloqueada ate #1050 crescer. #1482 (CORS em archive.org) tem workaround de codigo ja mesclado (#1521, Cloudflare Worker em deployment/archive-cors-proxy/) mas esta bloqueada em deploy real -- exige credenciais Cloudflare que esta sessao nao tem (confirmado: nenhuma env var CF_*/CLOUDFLARE_* presente). #1468-#1472 (cadeia Parquet/CNJ) permanecem bloqueadas por credenciais IA ausentes (confirmado em rodadas anteriores). Nenhuma issue aberta oferece um caminho de execucao imediato sem bloqueio externo alem de #1050."
---

# Leitura: issues abertas

`mcp__github__list_issues` (owner=franklinbaldo, repo=causaganha,
state=OPEN, orderBy=UPDATED_AT desc) retornou 22 issues. Mais
relevantes, verificadas nesta rodada:

- **#1050** ("segmenter: repair and scale the real training corpus with
  agent annotation") -- linhagem mais ativa do repositorio, 21 lotes
  reais ja mesclados (mecanismos AgentRun e Wisk alternando na mesma
  linhagem sem sobreposicao). Estado ao vivo confirmado nesta rodada via
  `scripts/segmenter_governance_status.py`: `document_count=167`,
  `annotation_count=220`, `review_count=31`, `val_count=25`,
  `test_count=6`, `val_ceiling=test_ceiling=25`,
  `meets_rfc_0012_split_floor=false`, `corpus_scale_blocks_floor=true`.
  O piso RFC 0012 Sec 5 item 4 (>=30 val, >=30 test adjudicados) nao e
  alcancavel nem com 100% de adjudicacao do pool atual -- precisa
  crescer o corpus total para aproximadamente `document_count>=200`
  (15% de 200 = 30). Cada lote historico adiciona ~6 documentos reais.
- **#1051** ("segmenter: build an independently annotated validation
  set") -- bloqueada estruturalmente ate #1050 elevar o teto (fato
  reconfirmado ao vivo pelo mesmo `segmenter_governance_status.py`
  acima: `corpus_scale_blocks_floor=true`).
- **#1482** (CORS em archive.org para `DuckDBExplorer.read_parquet()`)
  -- lida integralmente (issue body + 2 comentarios). Ja tem: deteccao/
  classificacao do bloqueio CORS mesclada (`DuckDBExplorer.cors-block-classification.test.ts`,
  mensagem "1482" explicita ao usuario), confirmacao real em browser
  via Playwright (`docs/planning/evidence/archive-cors-probe-real-browser.json`),
  e um workaround de codigo completo (#1521, Cloudflare Worker em
  `deployment/archive-cors-proxy/` + `PUBLIC_ARCHIVE_PROXY_BASE`) --
  mas o ultimo comentario (2026-09-15) explica que o Worker nunca foi
  de fato publicado por falta de credenciais Cloudflare naquela sessao.
  Esta sessao confirmou `env | grep -i cloudflare` / `CF_` vazio --
  mesmo bloqueio de credenciais persiste, issue permanece nao acionavel
  por codigo puro nesta rodada.
- **#1468-#1472** (cadeia Parquet/CNJ) -- linhagem Wisk paralela; #1471
  segue bloqueada por credenciais IA ausentes (fato ja confirmado por
  multiplas rodadas anteriores, fora do controle desta sessao).
- **#1053-#1057** (roadmap de treino do segmentador: baseline OPF,
  learning curves, benchmarks de encoder, experimentos de arquitetura)
  -- todos dependem de #1050 primeiro cruzar o piso RFC 0012 (val/test
  >=30), que ainda nao foi alcancado.

Conclusao: nenhuma issue aberta hoje oferece um caminho de execucao
imediato, sem bloqueio de credenciais externas, com tanto contexto
acumulado quanto #1050. A linhagem #1050 continua sendo a escolha mais
direta para avanco real nesta rodada.
