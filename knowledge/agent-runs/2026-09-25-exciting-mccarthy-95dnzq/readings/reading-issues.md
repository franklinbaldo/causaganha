---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-95dnzq-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-95dnzq"
subject: "open_issues"
reference: "mcp__github__list_issues(owner=franklinbaldo, repo=causaganha, state=OPEN) -- 28 issues abertas, lidas ao vivo no inicio da rodada"
finding: "Backlog de seguranca (docs/SECURITY_THREAT_MODEL.md Sec.5): #1608/#1612/#1615/#1611/#1610 ja fechadas por rodadas anteriores (a ultima, #1611/TM-05, mesclada minutos antes desta leitura como PR #1621; #1610/TM-03 parcialmente fechada como PR #1622, ainda em voo no momento desta leitura). Restam abertas na ordem de execucao: #1609/TM-02 (relays e DJEN proxy -- proximo item da ordem, o unico ainda nao tocado por nenhuma rodada), #950/TM-06 (rate limit do MCP publico), #1613/TM-08 (CSP), #1614/TM-10 (supply chain/build reprodutivel), #1616/TM-11 (contrato machine-readable para agentes). Cluster #1050/#1051 (corpus real do segmentador, RFC 0012): #1050 aberta, PR #1605 (28o lote nao, na verdade 27o lote) permanece com mergeable_state=dirty (conflito real, branch alheia claude/exciting-mccarthy-034xwb) ha 2+ dias -- reconfirmado sem fato novo, fora do alcance desta sessao sem permissao explicita de push naquela branch. Cluster Parquet/CNJ (#1470/#1469/#1482/#1471/#1472/#1468/#1022/#985): reconfirmado bloqueado por credenciais Internet Archive ausentes neste tipo de sessao, fato ja estabelecido por 10+ rodadas anteriores. #1353 (dependabot bump @vitest/mocker, deployment/relay-cf): parada ha 16 dias, baixa prioridade, fora de escopo. Demais issues (#951, #1093, #1047/#1053-#1057, #884/#886/#887) sao trabalho de produto/ML de longo prazo sem gate de seguranca urgente."
---

# Leitura: issues abertas

Leitura ao vivo via `mcp__github__list_issues` (28 issues abertas) no
inicio da rodada. O achado central: `#1609`/TM-02 e a proxima issue de
seguranca na ordem de execucao do threat model e ainda nao foi tocada
por nenhuma rodada anterior desta janela -- as issues antes dela na
ordem (`#1608`, `#1612`, `#1615`) ja estao fechadas, e `#1611` foi
fechada minutos antes desta leitura por uma sessao concorrente. `#1605`
(27o lote do corpus do segmentador) e `#1353` (dependabot) permanecem
fora de escopo pelos mesmos motivos ja registrados por rodadas
anteriores -- sem fato novo que os reabra.
