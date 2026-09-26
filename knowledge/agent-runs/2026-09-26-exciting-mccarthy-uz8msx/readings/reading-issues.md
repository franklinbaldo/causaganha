---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-uz8msx-reading-issues"
run_id: "2026-09-26-exciting-mccarthy-uz8msx"
subject: "open_issues"
reference: "GitHub issues abertas (franklinbaldo/causaganha, mcp__github__list_issues state=OPEN, 20 abertas)"
finding: "#950 (rollout MCP remoto) NÃO aparece na lista de issues abertas -- issue_read confirma state='closed', closed_at='2026-09-25T23:53:17Z', closed_by='franklinbaldo' (token/App desta linha de sessões), closed_by_pull_requests=[#1630, #1661]. Isso é uma surpresa: a rodada anterior (orr2e3, ~23:46Z) reabriu #950 explicitamente via issue_write citando deploy-mcp.yml com 0 execuções, e o PR #1661 que ela abriu tem no TÍTULO a frase 'reopen prematurely closed #950' -- mas o GitHub reconhece 'closed #950' (a palavra 'closed' é um sinônimo de keyword de fechamento, tanto quanto 'close'/'closes'/'fixed'/'resolved') em título/corpo/commit de PR como closing keyword. Ao mergear #1661 (23:53:16Z, 1s antes do closed_at de #950), o próprio GitHub reclosed a issue que a PR pretendia reabrir -- um auto-close acidental disparado pelo texto do próprio título da PR de correção, não uma ação humana ou de outra rodada. Nenhum commit/PR chamou issue_write com state=closed. Resto do backlog de issues abertas inalterado desde a última leitura (szlcz8, ~22h atrás): clusters #1468-1472 (Parquet/CNJ) e #1022/#985/#951/#1093 seguem bloqueados por credenciais IA ausentes ou por dependência de #950; cluster #1047-1057/#884/#886/#887 (segmenter RFC 0012) segue sem PR em voo; #1652 (TM-16) já fechada (confirmado issue_read separado, state='closed', todas as 3 fatias fechadas por PRs próprias mescladas: #1654/#1657/#1659)."
---

# Leitura: issues abertas
