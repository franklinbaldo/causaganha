---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-q4zn8q-decision-follow-scheduled-scaffold-again"
run_id: "2026-09-15-exciting-mccarthy-q4zn8q"
question: ".claude/hourly-loop.md e knowledge/agent-runs/index.md continuam declarando, sem ressalva, que o mecanismo AgentRun e legado e que novas rodadas devem usar exclusivamente o Wisk. Pelo menos 9 rodadas consecutivas ja identificaram essa tensao e decidiram seguir o scaffold mesmo assim, sem enviar nova notificacao desde 50ns70. O prompt agendado que disparou esta sessao nao mudou. Esta rodada deve criar mais um AgentRun, e deve enviar mais uma notificacao proativa sobre o mesmo conflito?"
choice: "Seguir a instrucao explicita do prompt agendado e criar este AgentRun (feito). Nao enviar nova notificacao proativa: nada mudou sobre o conflito em si desde a ultima avaliacao (afj2il, mesma manha). Escolher como foco de dominio a issue #1482 (proxy CORS para archive.org), em vez de repetir a escala de #1051 pela 14a+ vez hoje, por ser um bug de producao real, desbloqueado e ainda sem nenhuma tentativa de correcao."
rationale: "O ritual de notificacao existe para trazer atencao humana a uma condicao nova ou nao resolvida que precise de decisao. Notificar mais uma vez sobre exatamente o mesmo fato, sem nenhuma mudanca de estado desde a rodada anterior no mesmo dia, seria ruido. Quanto a escolha de trabalho: #1051 continua sendo escalado com sucesso por uma cadeia longa de rodadas ja bem estabelecida; diversificar o avanco do produto para #1482 -- uma frente real, unclaimed e sem bloqueio de credenciais -- produz mais valor incremental para o CausaGanha do que mais uma rodada identica as anteriores."
---

# Decisao: manter o scaffold AgentRun, sem nova notificacao, focar em #1482

Mesma linha de pelo menos 9 rodadas anteriores hoje e ontem: o prompt
agendado continua instruindo o scaffold `AgentRun` legado sem ressalva,
apesar de `.claude/hourly-loop.md` e `knowledge/agent-runs/index.md`
dizerem para nao criar novos. Sigo a instrucao explicita da sessao. Nao
envio nova notificacao proativa -- nada mudou sobre o conflito desde a
avaliacao mais recente (afj2il, mesma manha), e repetir o mesmo sinal sem
informacao nova seria ruido, nao sinal.

Trabalho desta rodada: implementar o workaround de proxy CORS sugerido
pela propria issue #1482 (nunca tentado por nenhuma rodada anterior),
seguindo TDD, em vez de continuar a cadeia de escala de #1051 pela 14a+
vez hoje.
