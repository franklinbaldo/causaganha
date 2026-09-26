---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-uz8msx-reading-okf"
run_id: "2026-09-26-exciting-mccarthy-uz8msx"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-25-exciting-mccarthy-{orr2e3,szlcz8,230b86,5txmmk}/run.md + docs/SECURITY_THREAT_MODEL.md"
finding: "orr2e3 (a rodada mais recente completada, ~23:24-00:05Z) reabriu #950 no GitHub via issue_write após descobrir que fora fechada indevidamente por PR #1630 (que só fechou o sub-item TM-06, não o critério de aceite real da issue -- deploy-mcp.yml com 0 execuções). O PR que essa rodada abriu para registrar a correção (#1661) tinha no título a string 'reopen prematurely closed #950' -- e o merge desse mesmo PR, ironicamente, reclosed a issue: GitHub trata 'closed #950' como closing keyword tanto quanto 'closes #950'. Isso não foi percebido pela rodada orr2e3 (que já havia terminado antes do merge acontecer via ação humana) nem por nenhuma rodada anterior -- é a primeira vez que esse padrão de auto-close acidental via título de PR aparece no histórico OKF lido. #1652 (TM-16, catalog/data poisoning via busca livre IA) fechou nesta mesma janela por 3 fatias próprias (230b86 direto em main, PR #1657 e PR #1659), confirmando o padrão estabelecido por dezenas de rodadas: preferir TDD próprio a adotar PRs externas (codex) desatualizadas -- reforçado por esta leitura ao ver #1643/#1644/#1645 (as PRs externas que tentaram os mesmos 3 itens) ainda abertas e agora sem trabalho útil a oferecer. szlcz8 já havia registrado a mesma preferência. Nenhuma rodada da janela de hoje escalou ao dono humano o bloqueio de #1605 (segmenter batch27, 8+ rodadas seguidas sem permissão de push na branch) -- item mais antigo do backlog sem novidade, não retomado nesta leitura por não ser o foco escolhido desta rodada."
---

# Leitura: OKF (rodadas recentes)
