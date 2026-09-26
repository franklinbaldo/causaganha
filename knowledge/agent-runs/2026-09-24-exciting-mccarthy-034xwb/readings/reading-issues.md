---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-034xwb-reading-issues"
run_id: "2026-09-24-exciting-mccarthy-034xwb"
subject: "open_issues"
reference: "mcp__github__list_issues franklinbaldo/causaganha state=OPEN"
finding: "22 issues abertas. #1050 (segmenter: repair/scale real training corpus) e a unica com trabalho imediatamente executavel e desbloqueado -- selecionada como goal. #1468-1472 (Parquet/CNJ) permanecem bloqueadas por credenciais IA ausentes (reconfirmado por multiplas rodadas anteriores, nenhum fato novo). #1482 (CORS no endpoint archive.org/download) tem workaround ja implementado em PR #1521 mesclada (Cloudflare Worker em deployment/archive-cors-proxy/), mas o proprio Worker nunca foi deployado por falta de credenciais Cloudflare nessa sessao anterior -- provavelmente bloqueado pelo mesmo motivo aqui (sem credencial Cloudflare disponivel neste ambiente). #1093 (busca publica de decisoes) esta explicitamente marcada 'ESPECIFICADA, mas NAO e prioridade imediata' pelo proprio corpo da issue, dependente de #950 primeiro. #1057/#1056/#1055/#1054/#1053/#1051/#1047 sao a fila de pos-corpus do segmentador (active learning, baseline OPF, validacao independente) -- todas dependem do corpus de #1050 atingir o piso RFC 0012 primeiro, portanto nao selecionaveis ainda. Nenhuma issue nova relevante desde a ultima leitura de hoje (my6ovw)."
---

# Leitura: issues abertas

Releitura das 22 issues abertas via `mcp__github__list_issues`. Estado
inalterado em relacao a ultima leitura de hoje mais cedo: `#1050`
continua sendo o unico item de trabalho real e desbloqueado; os
demais candidatos (Parquet/CNJ, proxy CORS do archive.org) dependem de
credenciais ausentes neste ambiente, e a fila pos-corpus do
segmentador (`#1051`/`#1053`-`#1057`) esta gated pelo piso RFC 0012
que `#1050` ainda nao cruzou.
