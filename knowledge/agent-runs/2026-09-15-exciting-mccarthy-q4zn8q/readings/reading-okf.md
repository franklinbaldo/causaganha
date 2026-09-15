---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-q4zn8q-reading-okf"
run_id: "2026-09-15-exciting-mccarthy-q4zn8q"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/index.md, .claude/hourly-loop.md, knowledge/agent-runs/2026-09-15-exciting-mccarthy-afj2il/run.md (rodada de continuidade mais recente mesclada em main, HEAD atual)"
finding: "knowledge/agent-runs/index.md e .claude/hourly-loop.md continuam declarando, sem ressalva, que o loop horário migrou para o runtime do Wisk e que novos AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck não devem ser criados aqui -- mesma tensão identificada por pelo menos 9 rodadas anteriores hoje e ontem (bueov4, to0ars, 50ns70, 5crg57, 6d5vnd, virf8r, wvzu11, yz281l, afj2il), todas decidindo seguir o scaffold porque o prompt agendado que dispara a sessão continua instruindo-o explicitamente, sem menção ao Wisk. Nada mudou desde a última avaliação (afj2il, mesma manhã) -- ver decision-follow-scheduled-scaffold-again desta rodada. afj2il (última rodada mesclada, HEAD atual, 8d7b02b) deixou como next_move continuar escalando #1051, mas também não descartou outras frentes desbloqueadas; a leitura de issues desta rodada identificou #1482 (proxy CORS) como uma frente real, desbloqueada e nunca tentada."
---

# Leitura: knowledge OKF

Reconfirmado ao vivo: `knowledge/agent-runs/index.md` e `.claude/hourly-loop.md`
seguem sem alteração desde a última avaliação (afj2il, poucas horas atrás)
-- o texto migratório para Wisk continua lá, mas o prompt agendado que
iniciou esta sessão continua pedindo explicitamente o scaffold `AgentRun`
legado, sem menção ao Wisk. Ver `decision-follow-scheduled-scaffold-again`
para a decisão tomada nesta rodada (mesma linha das 9 anteriores).

Diferente das últimas ~13 rodadas (que todas escalaram #1051), esta rodada
desvia para #1482 porque: (a) é um bug de produção real e confirmado, não
um item de checklist interno; (b) não depende de credenciais ausentes
(IA/Cloudflare), ao contrário do cluster #1468-1472; (c) a linhagem de hoje
já fechou tudo o que dependia só de confirmação/detecção (rodada 50ns70) e
explicitamente deixou o item de correção (proxy) como follow-up separado,
nunca reivindicado por nenhuma rodada posterior.
