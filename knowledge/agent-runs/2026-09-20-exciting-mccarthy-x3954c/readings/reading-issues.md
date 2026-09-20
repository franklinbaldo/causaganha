---
type: AgentReading
id: "2026-09-20-exciting-mccarthy-x3954c-reading-issues"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
subject: "open_issues"
reference: "mcp__github__issue_read (owner=franklinbaldo, repo=causaganha) sobre #1050, #1470, #1471; mcp__github__list_issues truncado por tamanho, contornado consultando issues especificas ja conhecidas de rodadas anteriores"
finding: "#1050 (corpus real do segmentador) permanece a linhagem mais ativa: document_count=191, annotation_count=244 apos o lote 25 (PR #1594, ja mesclado antes desta rodada). O piso RFC 0012 Sec 5 item 4 (>=30 val, >=30 test adjudicados) ainda nao e alcancavel (val_ceiling=test_ceiling=29 nesta rodada). #1470 (auditoria de catalogo Parquet/CNJ) foi atualizada na rodada anterior (11/09->20/09, sem credenciais IA necessarias) e nao tem trabalho pendente obvio para esta rodada. #1471 (piloto de reordenacao TJRO 2026) permanece bloqueada por credenciais IA ausentes, reconfirmado por multiplas rodadas incluindo a imediatamente anterior. Nenhuma issue aberta oferecia um caminho de execucao imediato sem bloqueio -- o avanco real desta rodada veio de uma investigacao ao vivo (script `segmenter_governance_status.py` travando por minutos), nao da fila de issues, mas serve diretamente a #1050 ao destravar o proprio script de verificacao que cada lote do #1050 usa."
---

# Leitura: issues abertas

Como `mcp__github__list_issues` (state=OPEN) excedeu o limite de
tokens da ferramenta (73KB), esta rodada consultou diretamente as
issues mais relevantes ja conhecidas de rodadas anteriores via
`mcp__github__issue_read`:

- **#1050** ("segmenter: repair and scale the real training corpus
  with agent annotation") -- ainda aberta, 3 comentarios, sem PR que a
  feche formalmente (`closed_by_pull_requests.total_count=0`; os PRs de
  lote referenciam a issue no titulo mas nao a fecham, correto -- e um
  trabalho continuo). 25 lotes reais ja mesclados antes desta rodada.
- **#1470** ("Parquet/CNJ: auditar o catalogo e decidir regeneracao
  por arquivo") -- atualizada em 20/09/2026 pela rodada imediatamente
  anterior (refresh de 24->61 arquivos auditados, 0 perdas). Nao
  oferece proximo passo obvio sem reler a evidencia completa dessa
  rodada; nao selecionada.
- **#1471** ("Parquet/CNJ: validar piloto TJRO 2026") -- depende de
  #1469 e #1470, bloqueada por credenciais IA ausentes (confirmado por
  >=11 rodadas consecutivas, incluindo a anterior). Sem fato novo nesta
  rodada (nenhuma credencial `IA_*`/`ARCHIVE_*` presente no ambiente).

Nenhuma dessas tres ofereceu um caminho de execucao imediato e
verificavel sem bloqueio de credenciais ou sem duplicar trabalho ja em
andamento em PR aberta (ver `reading-prs`). O trabalho efetivamente
selecionado nesta rodada nasceu de uma observacao ao vivo durante a
tentativa de rodar `scripts/segmenter_governance_status.py` (o
primeiro passo natural antes de qualquer novo lote de #1050): o script
ficou travado por mais de 8 minutos de CPU a 99.9%, muito acima do
comportamento historico documentado em rodadas anteriores ("confirmado
ao vivo" instantaneo em ~20 relatorios anteriores). Isso nao e uma
issue GitHub aberta, mas e um bloqueio real e imediato ao proximo passo
natural de #1050 -- descrito e resolvido nesta rodada (ver
`goal-dedup-quadratic-fix`).
