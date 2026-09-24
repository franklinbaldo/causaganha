---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-khpkk2-reading-issues"
run_id: "2026-09-24-exciting-mccarthy-khpkk2"
subject: "open_issues"
reference: "mcp__github__list_issues / list_pull_requests, franklinbaldo/causaganha, 2026-09-24"
finding: "22 issues abertas, quase todas da linhagem #1050 (segmentador, RFC 0012) ou do workstream Parquet/CNJ (#1468-#1472, com #1471 confirmado bloqueado por credenciais IA ausentes -- reconfirmado ao vivo nesta rodada via 'uv run wisk start', ver reading-okf). Nao existe issue dedicada 'AgentRun vs Wisk'; o registro mais proximo e a issue #1256 (fechada 2026-09-07), que decidiu formalmente aposentar o AgentRun como loop operacional em favor do Wisk -- ver reading-okf para a analise completa dessa tensao com o prompt agendado desta sessao."
---

# Leitura: issues abertas

`mcp__github__list_issues` (state=open) retornou 22 issues. A grande
maioria pertence a duas frentes ja mapeadas por rodadas anteriores:

- **#1050** (ativa) e seu conjunto de issues-irmas (#1051, #1053-#1057,
  #884, #886-#887): a linhagem do corpus real de treino do
  segmentador (RFC 0012), com `document_count`/`val_ceiling`/
  `test_ceiling` como sinais de progresso.
- **#1468-#1472**: workstream de regeneracao do catalogo Parquet/CNJ.
  `#1471` (validar piloto TJRO 2026) permanece bloqueada por
  credenciais IA ausentes -- reconfirmado ao vivo nesta rodada (12a+
  rodada consecutiva a bater no mesmo blocker), nao acionavel sem
  intervencao humana externa.

Nenhuma issue aberta trata de "AgentRun" ou "Wisk" diretamente. A
peca de contexto relevante e a **issue #1256** (fechada em
2026-09-07 pelo proprio dono do repositorio, sem thread de
comentarios): decidiu que o CausaGanha deve usar exclusivamente o
Wisk como runtime do ciclo continuo, mantendo `knowledge/agent-runs/`
apenas como historico legado, e instruiu que "novas rodadas nao devem
criar AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/
AgentCheck". A issue nao fala sobre o gatilho agendado que ainda
dispara o scaffold antigo (`.claude/agent-run-scaffold.md`) -- essa
lacuna e o cerne da tensao ja documentada por 5 rodadas anteriores
(ver `reading-okf` e `decision-*` desta rodada).
