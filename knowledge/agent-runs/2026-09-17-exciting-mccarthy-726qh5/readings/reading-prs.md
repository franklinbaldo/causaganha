---
type: AgentReading
id: "2026-09-17-exciting-mccarthy-726qh5-reading-prs"
run_id: "2026-09-17-exciting-mccarthy-726qh5"
subject: "open_prs"
reference: "github:franklinbaldo/causaganha pulls state=open (2 abertas em 2026-09-17T02:25Z)"
finding: "Apenas duas PRs abertas: #1574 (lote 17 do corpus do segmentador para #1050, sessao concorrente 0hjgmk, branch claude/exciting-mccarthy-0hjgmk, CI ainda pendente/sem status, mergeable_state=unstable) e #1353 (dependabot, bump @vitest/mocker, sem relacao com o trabalho desta rodada). #1574 ja lista os 5 documentos que consumiu (TJBA/574460085, TJMA/42736393, TJMA/42730832, TJCE/363647616, TJCE/363657243) e um sexto descartado por quase-duplicata (TJBA/574460088) -- esses IDs devem ser excluidos de qualquer selecao de candidatos desta rodada para evitar a colisao ja documentada nas classes de risco 9/12 de issue-1050.md."
---

# Leitura: PRs abertas

`mcp__github__list_pull_requests` (state=open) retornou apenas duas
entradas:

1. **#1574** -- `feat(segmenter): ingest seventeenth real multi-tribunal
   batch via Technique 1 (#1050)`, aberta 2026-09-17T02:05Z por uma
   sessao diferente desta (branch `claude/exciting-mccarthy-0hjgmk`,
   sessao `session_015ZizZNXacDRHoNXq9Sn3Sw`). `pull_request_read
   get_status` retornou `state: pending, total_count: 0` -- CI ainda nao
   reportou nenhum check no momento da leitura. `mergeable_state:
   unstable`. O corpo da PR documenta: document_count 138->143,
   annotation_count 191->196, val/test ceiling inalterado em 21/21
   (lote train-only). Um bug real de producao foi corrigido no script
   de remapeamento NBSP reutilizado desde o lote 15 (limite de um
   diff multi-caractere mapeado incorretamente, podendo apagar uma tag
   XML silenciosamente) -- ja fica registrado para nao ser
   redescoberto. Esta PR nao foi criada por esta sessao nem esta sessao
   foi pedida para observa-la (nenhuma inscricao `subscribe_pr_activity`
   ativa) -- nao vou empurrar commits para o branch dela nem tratar seu
   CI como responsabilidade desta rodada; apenas evito colidir com os
   candidatos que ela ja consumiu.
2. **#1353** -- PR do dependabot (bump `@vitest/mocker` em
   `deployment/relay-cf`), parada desde 2026-09-09, sem relacao com
   qualquer issue considerada nesta rodada; nao e o melhor uso do tempo
   desta sessao (bump de dependencia de dev/test isolado, sem sinal de
   quebra ou urgencia).

Nenhuma outra PR aberta compete pelo mesmo lote de trabalho. A decisao
desta rodada (ver decisions/) e continuar a linhagem #1050 com um lote
18 cujos candidatos excluem explicitamente os 6 IDs listados no corpo
de #1574 (5 ingeridos + 1 descartado por quase-duplicata), reduzindo o
risco de colisao a quase zero mesmo que #1574 ainda nao tenha mesclado
quando esta rodada abrir sua propria PR.
