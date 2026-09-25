---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-230b86-reading-okf"
run_id: "2026-09-25-exciting-mccarthy-230b86"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-25-exciting-mccarthy-qjwekj/run.md (relatorio mais recente concluido antes desta rodada, iniciada 16:20Z) e knowledge/okf.schema.sql"
finding: "qjwekj (rodada mais recente concluida antes desta) fechou o lado de leitura de TM-04 para juris via PR #1648 mesclada e confirmou #1482 fechada. Seu next_move apontava: (1) lado de leitura do TM-04 para juris -- ja fechado por outra rodada intermediaria (PR #1650, mesclada antes desta rodada comecar, ver git log); (2) KV_METADATA para stj -- reconfirmado nesta rodada como genuinamente fora de alcance (sem pipeline de export); a fatia real e tratavel era datajud, nao stj, e foi fechada nesta rodada via PR #1651; (3) reconfirmar #1605 -- sem fato novo, nao reinvestigado do zero; (4) avaliar overlap entre PRs codex/aardvark (#1643/#1644/#1645) e #1610/TM-03 -- feito nesta rodada pela primeira vez em profundidade (ver reading-prs.md): overlap topico (superficies IA nao confiaveis) mas nao overlap de arquivos, e a ameaca real que essas PRs cobrem (descoberta/catalog poisoning) nao e TM-03/TM-04, e sim uma classe nova, agora TM-16/#1652; (5) reler SECURITY_THREAT_MODEL.md por completo para confirmar status de #1610 -- feito, TM-04 sem gap tratavel restante apos #1651, decisao registrada sobre fechar #1610. Leitura de knowledge/okf.schema.sql confirmou os nomes de campo exatos das tabelas AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck antes de escrever qualquer arquivo desta rodada."
---

# Leitura: conhecimento OKF relevante

Revisado o relatório `AgentRun` mais recente concluído antes desta rodada
(`qjwekj`, 16:20Z) e o schema relacional `knowledge/okf.schema.sql`. Uma
rodada intermediária (`r0zxiq`, cuja PR `#1651` esta rodada mesclou) já
havia avançado o `next_move` de `qjwekj` nos itens (1)/(2) com a fatia
`datajud` de TM-04. O item (4) do `next_move` de `qjwekj` — avaliar overlap
das PRs `codex`/`aardvark` com `#1610`/TM-03 — não havia sido investigado a
fundo por nenhuma rodada anterior apesar de repetido em 3+ `next_move`
consecutivos; esta rodada o resolveu, concluindo que a ameaça real não é
TM-03/TM-04 e sim uma classe nova (`TM-16`, issue `#1652`).
