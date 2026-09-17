---
type: AgentReading
id: "2026-09-17-exciting-mccarthy-91jobr-reading-okf"
run_id: "2026-09-17-exciting-mccarthy-91jobr"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/index.md, .claude/hourly-loop.md, knowledge/agent-runs/2026-09-14-exciting-mccarthy-to0ars/decisions/decision-agentrun-vs-wisk-policy-conflict.md, knowledge/backlog/issue-1050.md, knowledge/agent-runs/2026-09-17-exciting-mccarthy-0hjgmk/run.md"
finding: "A tensao AgentRun-vs-Wisk permanece sem reconciliacao do dono humano havendo agora um sinal mais forte que na ultima leitura: knowledge/agent-runs/index.md (o proprio diretorio-alvo do scaffold agendado) foi atualizado desde a ultima rodada com um aviso em negrito no topo dizendo explicitamente para nao criar novos AgentRuns. A escalada de 2026-09-14 (to0ars) segue sem resposta, e agora ha evidencia concreta de custo (duas PRs simultaneas #1576/#1577 para o mesmo 'lote 18'), nao apenas risco teorico -- fato novo que justifica reescalar ao final desta rodada."
---

# Leitura: conhecimento OKF relevante

## Tensao AgentRun vs. Wisk -- agora com sinal mais forte e custo concreto

`.claude/hourly-loop.md` ja tratava o scaffold AgentRun como legado
historico em favor do Wisk. Desde a ultima rodada (0hjgmk),
`knowledge/agent-runs/index.md` -- o proprio README do diretorio que o
prompt agendado desta sessao instrui a popular -- ganhou um aviso em
negrito explicito: "Não crie novos AgentRun, AgentReading, AgentGoal,
AgentDecision, AgentEvidence ou AgentCheck aqui." A decisao
`2026-09-14-exciting-mccarthy-to0ars-decision-agentrun-vs-wisk-policy-
conflict` ja escalou este exato conflito via notificacao proativa; pelo
menos 7 rodadas desde entao reconfirmaram a mesma decisao sem mudanca no
agendamento.

O fato novo desta rodada: o conflito deixou de ser teorico. Duas PRs
abertas simultaneamente (#1576 desta linhagem AgentRun, #1577 do Wisk)
reivindicaram o mesmo numero de lote ("decimo oitavo") para #1050 dentro
de uma janela de poucos minutos (03:30Z e antes) em 2026-09-17. O Wisk
mesclou primeiro (`0a831be`); a PR AgentRun ficou organicamente stale
com 6 documentos reais e ja anotados, mas nao descartaveis sem
desperdicar trabalho real de subagente. Isso e evidencia concreta de
custo (CI duplicado, revisao duplicada, trabalho de resgate necessario)
que nao existia na ultima leitura -- justifica reescalar ao dono ao
final desta rodada com esse fato novo, seguindo o mesmo precedente de
nao mudar de mecanismo unilateralmente.

## Estado real do corpus (verificado ao vivo nesta rodada)

`scripts/segmenter_governance_status.py`: `document_count=149`,
`annotation_count=202`, `review_count=31`, `val_ceiling=test_ceiling=22`,
`corpus_scale_blocks_floor=true` contra o piso RFC 0012 Sec 5 item 4
(>=30 val, >=30 test). `meets_rfc_0012_split_floor=false`.

## Trabalho selecionado

Resgatar o conteudo real da PR #1576 (6 documentos/anotacoes reais e
distintos, ja validados por fidelidade verbatim pela sessao anterior)
aplicando o mesmo payload sobre a branch propria desta sessao
(`claude/exciting-mccarthy-91jobr`), renumerando as evidencias de
auditoria de "lote 18" para "lote 19" para eliminar a colisao de nome,
atualizando `knowledge/backlog/issue-1050.md` e reverificando
`scripts/segmenter_governance_status.py` antes de abrir uma nova PR e
fechar a #1576 como superada/resgatada.
