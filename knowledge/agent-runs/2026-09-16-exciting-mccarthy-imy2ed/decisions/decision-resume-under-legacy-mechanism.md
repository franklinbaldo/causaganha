---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-imy2ed-decision-resume-under-legacy-mechanism"
run_id: "2026-09-16-exciting-mccarthy-imy2ed"
goal_id: "2026-09-16-exciting-mccarthy-imy2ed-goal-djen-sample-batch10"
question: ".claude/hourly-loop.md declara o mecanismo AgentRun (este scaffold) 'legado historico' em favor do runtime Wisk, mas o prompt armazenado desta tarefa agendada instrui explicitamente, em detalhe, o mecanismo AgentRun como primeira acao da sessao. Seguir o prompt armazenado ou trocar para Wisk sem instrucao?"
choice: "Segui o prompt armazenado desta tarefa agendada como instruido, reusando o raciocinio ja registrado por 3 rodadas anteriores da mesma data (83kr8s, k5wsee, c4y4rc) em vez de rederivar. Nao editei .claude/hourly-loop.md nem knowledge/agent-runs/index.md para relitigar a depreciacao, e nao enviei nova notificacao ao dono humano porque nao ha fato novo desde a ultima avaliacao (2026-09-14) -- apenas mais uma rodada confirmando o mesmo estado ja reportado."
rationale: "A tensao e real mas ja esta documentada e reportada; relitigar em cada rodada so desperdicaria trabalho sem produzir sinal novo para o operador. Trocar de mecanismo unilateralmente no meio de uma tarefa agendada cujo prompt e explicito e detalhado sobre o AgentRun ser 'o roteiro operacional da sessao' seria uma decisao arquitetural que cabe ao dono humano do agendamento, nao a esta sessao. O trabalho de dominio (mineracao real de corpus para #1050) e igualmente valioso independente de qual mecanismo de relatorio o envolve."
---

# Decisao: manter o mecanismo AgentRun nesta rodada

Ver `knowledge/agent-runs/2026-09-16-exciting-mccarthy-83kr8s/decisions/decision-continue-under-legacy-mechanism-despite-deprecation.md`
para o raciocinio original, que esta decisao reutiliza sem alteracao
material.
