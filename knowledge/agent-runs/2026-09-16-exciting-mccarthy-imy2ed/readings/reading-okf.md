---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-imy2ed-reading-okf"
run_id: "2026-09-16-exciting-mccarthy-imy2ed"
subject: "okf_knowledge"
reference: "knowledge/backlog/issue-1050.md, .claude/hourly-loop.md, knowledge/agent-runs/2026-09-16-exciting-mccarthy-83kr8s/decisions/decision-continue-under-legacy-mechanism-despite-deprecation.md, knowledge/agent-runs/2026-09-16-exciting-mccarthy-k5wsee/run.md"
finding: "knowledge/backlog/issue-1050.md documenta 8 lotes reais ja mesclados hoje (document_count 61->109), teto val/test em 16/16, e 6 classes de risco/defeito mapeadas (a 5a ja corrigida em codigo de producao no lote 7). .claude/hourly-loop.md declara explicitamente o mecanismo AgentRun (este scaffold) como 'legado historico' em favor de um novo runtime Wisk (.wisk/knowledge/) para o loop horario -- tensao ja identificada e registrada por pelo menos 3 rodadas anteriores (83kr8s, k5wsee, c4y4rc) sem reconciliacao do dono humano e sem fato novo desde 2026-09-14. Seguindo o mesmo raciocinio explicito ja registrado em decision-continue-under-legacy-mechanism-despite-deprecation.md (83kr8s): o prompt armazenado desta tarefa agendada especifica instrui, em detalhe, o mecanismo AgentRun como primeira acao da sessao -- segui-lo, sem relitigar a depreciacao nem criar um relatorio concorrente sob .wisk/. `uv run okf-parser check knowledge --relational-schema okf.schema.sql` estava conformant antes desta rodada tocar o bundle (nenhum AgentRun em rascunho pendente de rodada concorrente)."
---

# Leitura: conhecimento OKF relevante

Li `knowledge/backlog/issue-1050.md` (rastreamento vivo da linhagem),
`.claude/hourly-loop.md` (politica atual do loop horario) e a decisao
`decision-continue-under-legacy-mechanism-despite-deprecation.md` da
rodada 83kr8s, que ja enfrentou e resolveu exatamente esta mesma tensao
hoje. Adoto o mesmo raciocinio em vez de rederivar: o prompt armazenado
desta tarefa agendada e explicito e detalhado sobre o mecanismo AgentRun
ser "o roteiro operacional da sessao" -- sobrescrever isso unilateralmente
com base em uma politica que outra sessao decidiu depois de este prompt
ter sido configurado e uma decisao do operador humano, nao desta sessao.
Nao editei `.claude/hourly-loop.md` nem `knowledge/agent-runs/index.md`
para relitigar a depreciacao (ja registrada, sem fato novo que justifique
nova notificacao). Rodei `okf-parser check` antes de qualquer mudanca:
bundle conformant.
