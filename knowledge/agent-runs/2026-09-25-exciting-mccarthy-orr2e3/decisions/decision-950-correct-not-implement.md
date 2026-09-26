---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-orr2e3-decision-950-correct-not-implement"
run_id: "2026-09-25-exciting-mccarthy-orr2e3"
goal_id: "2026-09-25-exciting-mccarthy-orr2e3-goal-950-reopen"
question: "Encontrado que #950 (rollout MCP remoto) foi fechada sem cumprir seu critério de aceite -- esta rodada deveria tentar executar o rollout real (deploy-mcp.yml via workflow_dispatch) para fechar a issue de verdade, ou apenas corrigir o estado do rastreador?"
choice: "Apenas corrigir o estado do rastreador (reabrir #950 com comentário factual, reconciliar knowledge/backlog/issue-950.md e issue-951.md). Não tentar disparar deploy-mcp.yml nem fabricar prova de rollout."
rationale: "O ambiente desta sessão não expõe as credenciais GCP Workload Identity/service account que o próprio workflow `deploy-mcp.yml` exige como `workflow_dispatch` inputs (`project_id`, `workload_identity_provider`, `service_account`, etc.) -- confirmado por 6+ comentários de rodadas anteriores (2026-09-01 a 2026-09-07, ver reading-okf.md) que já diagnosticaram exatamente essa mesma fronteira. CLAUDE.md/instruções desta rodada são explícitas: nunca fabricar URL, nunca declarar rollout live sem prova real -- disparar o workflow sem autoridade real seria impossível, e inventar uma prova seria o oposto do que esta rodada está corrigindo. A ação de maior valor disponível é impedir que o rastreador continue afirmando algo falso, não tentar (e falhar) a implementação operacional em si."
---

# Decisão: corrigir o rastreador, não simular o rollout

Sem credenciais de deploy Cloud Run/GCP disponíveis nesta sessão (mesma
fronteira diagnosticada por 6+ rodadas anteriores entre 2026-09-01 e
2026-09-07), a única ação honesta é reabrir `#950` e reconciliar o
backlog local com o estado real -- não fabricar uma execução de deploy
que esta sessão não pode de fato realizar.
