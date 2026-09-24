---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-mjd1vm-reading-issues"
run_id: "2026-09-24-exciting-mccarthy-mjd1vm"
subject: "open_issues"
reference: "mcp__github__list_issues (owner=franklinbaldo, repo=causaganha, state=OPEN), 22 total, orderBy=UPDATED_AT desc"
finding: "Nenhuma issue nova desde a ultima leitura (fv62kx, 2026-09-20). #1050 continua a linhagem mais ativa com caminho de execucao provado (25 lotes reais mesclados desde entao: batch24/#1590, batch25/#1594). #1470 teve um refresh de auditoria (PR #1595, mesclada). #1051 continua estruturalmente bloqueada ate #1050 cruzar o piso RFC 0012. #1482 e #1468/1469/1471/1472 seguem bloqueadas por credenciais externas ausentes nesta sessao (confirmado: sem env CF_*/CLOUDFLARE_* e sem credenciais IA). O trabalho real e mais urgente desta rodada nao esta nas issues, e sim em tres PRs abertas e paradas ha 4 dias (ver leitura de PRs)."
---

# Leitura: issues abertas

`mcp__github__list_issues` (owner=franklinbaldo, repo=causaganha,
state=OPEN, orderBy=UPDATED_AT desc) retornou 22 issues, a mesma
contagem da ultima leitura registrada. Mais relevantes, reverificadas
nesta rodada:

- **#1050** -- linhagem mais ativa do repositorio. Desde a ultima
  leitura (fv62kx, document_count=179), dois lotes reais adicionais
  mergearam: batch24 (PR #1590, document_count 179->184/185) e batch25
  (PR #1594, document_count 184/185->191, val_ceiling=test_ceiling=29).
  Ainda abaixo do piso RFC 0012 Sec 5 item 4 (>=30/>=30). Duas PRs de
  correcao pos-batch25 seguem abertas e nao mescladas ha 4 dias: #1597
  (Codex findings do batch25) e #1598 (perf fix em dedup.py que
  desbloqueia rodar `segmenter_governance_status.py` sem travar).
- **#1051** -- continua bloqueada estruturalmente (corpus ainda abaixo
  do piso de #1050).
- **#1470** -- refresh de auditoria concluido e mesclado (PR #1595,
  2026-09-20): 0 arquivos perdidos, 37 novos arquivos ja certificados
  na ordem CNJ por padrao (issue #1469 confirmada como caminho
  default).
- **#1482** (CORS em archive.org) -- workaround de codigo (#1521)
  ja mesclado, mas bloqueado em deploy real por credenciais Cloudflare
  ausentes (`env | grep -i cloudflare` vazio nesta sessao tambem,
  reconfirmado).
- **#1468/#1469/#1471/#1472** (cadeia Parquet/CNJ) -- #1469 (escrita
  unificada) parece resolvida na pratica (ver achado de #1470 acima);
  #1471 segue bloqueada por credenciais IA ausentes ha 11+ rodadas
  consecutivas segundo o ultimo achado registrado (a914d57).
- **#1053-#1057** (roadmap de treino do segmentador) -- dependem de
  #1050 cruzar o piso RFC 0012 primeiro.

Conclusao: nenhuma issue aberta oferece hoje um caminho de execucao
mais direto e menos duplicativo do que terminar o trabalho ja
comecado e parado em #1597/#1598 (ver leitura de PRs) -- ambas tocam
exatamente a linhagem #1050/#1050-adjacente ja mapeada aqui, sem
bloqueio de credenciais externas.
