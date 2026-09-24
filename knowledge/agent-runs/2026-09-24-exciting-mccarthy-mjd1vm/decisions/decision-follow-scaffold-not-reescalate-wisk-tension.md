---
type: AgentDecision
id: "2026-09-24-exciting-mccarthy-mjd1vm-decision-follow-scaffold-not-reescalate-wisk-tension"
run_id: "2026-09-24-exciting-mccarthy-mjd1vm"
question: "O prompt agendado desta sessao continua instruindo explicitamente o scaffold AgentRun legado, mas .claude/hourly-loop.md (commitado no repo) diz que novas rodadas devem usar exclusivamente o Wisk e nao criar novos AgentRuns; alem disso, o repositorio ficou 4 dias sem nenhum commit em qualquer mecanismo, e o proprio dono humano abriu uma PR (#1599) formalizando o contrato de closeout do Wisk durante essa janela. Isso e fato novo suficiente para reescalar a tensao AgentRun-vs-Wisk (ja escalada uma vez em to0ars, 2026-09-14) via notificacao, ou para esta rodada trocar unilateralmente para `wisk start`?"
choice: "Cumprir o scaffold AgentRun como o prompt agendado pede nesta rodada (mesma decisao de to0ars), sem trocar unilateralmente para Wisk e sem reescalar via notificacao proativa. #1599 e evidencia de que o dono ja esta pessoalmente ativo nessa exata questao -- reescalar agora seria redundante, nao informativo."
rationale: "A decisao original de to0ars ja estabeleceu que uma rodada autonoma nao deve desligar seu proprio mecanismo de agendamento com base na sua propria leitura de um documento do repo, e que reescalar repetidamente sem fato novo satura o sinal (16+ rodadas ja reconfirmaram a tensao sem mudanca). O gap de 4 dias e novo, mas nao e por si so acionavel por esta sessao (causa fora do escopo observavel: agendamento, credenciais, pausa deliberada do dono). A abertura de #1599 pelo proprio franklinbaldo durante essa janela, porem, e o tipo exato de fato que tornaria uma notificacao redundante: ele ja esta escrevendo a politica que resolveria essa tensao. Notificar 'ainda ha uma tensao entre AgentRun e Wisk' para alguem que acabou de abrir uma PR sobre exatamente isso nao ajudaria -- desperdicaria a atencao que a rotina agendada deve proteger. O uso mais util desta rodada e concreto: finalizar trabalho de codigo ja comecado e parado (#1597/#1598), que avanca o produto independente de qual mecanismo de relatorio prevalecer no futuro."
---

# Decisão: seguir o scaffold, não reescalar a tensão AgentRun-vs-Wisk

O gap de 4 dias sem commits e a existência da PR #1599 (do próprio
dono, formalizando o contrato de closeout do Wisk) são fatos novos
desde a última confirmação da tensão AgentRun-vs-Wisk, mas nenhum dos
dois pede uma decisão humana urgente que esta sessão possa entregar
via notificação: o gap não tem causa observável daqui, e #1599 já
mostra o dono ativamente trabalhando o assunto. Esta rodada segue o
scaffold como instruído e usa o tempo da rodada para terminar trabalho
de código real e parado (#1597/#1598), que serve o produto
independentemente de qual mecanismo de relatório um dono humano
eventualmente escolher.
