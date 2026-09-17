---
type: AgentReading
id: "2026-09-17-exciting-mccarthy-726qh5-reading-issues"
run_id: "2026-09-17-exciting-mccarthy-726qh5"
subject: "open_issues"
reference: "github:franklinbaldo/causaganha issues state=OPEN (22 abertas em 2026-09-17)"
finding: "Das 22 issues abertas, 21 estao bloqueadas ou despriorizadas por causas externas ja documentadas em knowledge/backlog/*.md (credenciais IA/Cloudflare ausentes neste ambiente, decisao de hosting/produto pendente, ou trabalho de GPU/anotacao humana fora do alcance de uma sessao nao supervisionada); a unica issue com status 'unblocked' e continuamente provada por 17 lotes mesclados e #1050 (corpus real do segmentador), que ja tem uma PR aberta e concorrente desta mesma rodada (#1574, sessao 0hjgmk, branch claude/exciting-mccarthy-0hjgmk, CI ainda pendente no momento da leitura)."
---

# Leitura: issues abertas

Passei pelas 22 issues abertas do repositorio e cruzei cada uma contra
`knowledge/backlog/issue-<n>.md` quando existente, confirmando ao vivo
que a razao de bloqueio continua valendo (nenhuma credencial nova
apareceu neste ambiente: `env | grep -iE 'IAS3|IA_ACCESS|IA_SECRET|ARCHIVE|CLOUDFLARE|CF_API'`
nao retornou nada):

- **#1050** (segmenter, corpus real) -- `status: unblocked`. 17 lotes ja
  mesclados via `scripts/ingest_djen_sample_technique1_batch.py`
  (document_count historico 61->143 pelo body da PR #1574, ainda a
  confirmar ao vivo nesta rodada). Unica issue com caminho de execucao
  provado e sem bloqueio externo.
- **#1051** (validation set independente) -- sem arquivo de backlog
  proprio, mas a propria `issue-1050.md` explica que o piso RFC 0012
  Sec 5 item 4 (>=30 val/test adjudicados) ainda nao foi atingido
  (val/test ceiling em 21 apos o lote 16); nao e o proximo passo real
  ainda.
- **#1468-1472** (Parquet/CNJ: normalizacao, ordenacao fisica, leitura
  compatível) -- todo criterio alcancavel sem escrita real no Internet
  Archive ja esta implementado, testado e em `main` (confirmado por
  comentario de sync de status de #1469, 2026-09-15). O unico trabalho
  restante e a republicacao real do acervo reordenado (#1472),
  bloqueada por `IA_ACCESS_KEY`/`IA_SECRET_KEY` ausentes neste
  ambiente -- confirmado ao vivo, nao herdado sem checagem.
- **#1482** (CORS em archive.org/download) -- o workaround de codigo
  (proxy Cloudflare Worker + `PUBLIC_ARCHIVE_PROXY_BASE`) ja foi
  implementado e mesclado (#1521); a probe real de browser via
  Playwright ja roda agendada em CI (`.github/workflows/archive-cors-probe.yml`,
  cron semanal + workflow_dispatch), fechando a sugestao #3 do proprio
  issue. O unico passo restante e o deploy real do Worker, que exige
  credenciais Cloudflare ausentes neste ambiente (confirmado ao vivo).
  Nao havia `knowledge/backlog/issue-1482.md` documentando esse estado
  -- lacuna de higiene OKF que esta rodada corrige (ver decisao).
- **#950/#951** (MCP remoto) -- decisao de hosting/produto pendente do
  dono humano, nao um code change.
- **#1022** (Parquet TCU no IA) e **#985** (dataset TSE) -- ambos
  bloqueados por credenciais/acesso de rede externos ausentes.
- **#1093** -- despriorizada explicitamente pelo proprio corpo da issue
  ("NAO e prioridade imediata").
- **#884, #886, #887, #1047, #1053-#1057** (familia de experimentos do
  segmentador: baseline OPF, active learning, benchmarks, etc.) --
  todas exigem GPU, rodadas de active learning ou anotacao humana fora
  do alcance de uma sessao horaria nao supervisionada; `blocking_reason`
  identico ja documentado e ainda valido.

PRs abertas (ver reading-prs.md) confirmam que #1050 esta sendo
trabalhada ao vivo por uma sessao concorrente (PR #1574) no exato
momento desta leitura -- risco de colisao de candidatos ja documentado
extensivamente em `knowledge/backlog/issue-1050.md` (classes de risco
9/12). Isso pesa diretamente na selecao de goal desta rodada.
