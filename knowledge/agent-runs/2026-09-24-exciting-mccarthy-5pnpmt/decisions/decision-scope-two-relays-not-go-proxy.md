---
type: AgentDecision
id: "2026-09-24-exciting-mccarthy-5pnpmt-decision-scope-two-relays-not-go-proxy"
run_id: "2026-09-24-exciting-mccarthy-5pnpmt"
goal_id: "2026-09-24-exciting-mccarthy-5pnpmt-goal-relay-egress-policy"
question: "#1609/TM-02 cobre tres superficies (relay Python, relay CF, DJEN proxy Go). O DJEN proxy Go hoje nao tem NENHUMA autenticacao (diferente dos dois relays, que ja tem token) e o arquivo rastreado deployment/djen_proxy.go diverge do script Go embutido em deployment/DEPLOY_DJEN_V4.sh (que gera uma versao mais elaborada com graceful shutdown na hora do deploy) -- nao esta claro qual dos dois e a fonte de verdade do que roda em producao hoje. Fechar #1609 por completo nesta rodada (os 3 arquivos) ou fechar so os 2 relays e deixar o DJEN proxy Go para uma rodada dedicada?"
choice: "Fechar nesta rodada apenas os dois relays HTTP (deployment/relay/function/main.py e deployment/relay-cf/src/index.js), que compartilham o mesmo modelo de autenticacao (X-Relay-Token) e ja tem suites de teste dedicadas (tests/deployment/relay/test_main.py, deployment/relay-cf/test/index.test.js). Deixar deployment/djen_proxy.go como gap explicito registrado em next_move, sem tocar o arquivo nesta rodada."
rationale: "Adicionar autenticacao a um endpoint hoje publico sem token (o DJEN proxy) e uma mudanca de modelo de seguranca diferente de 'apertar uma politica ja existente' (o que esta rodada faz nos dois relays) -- exige coordenar rotacao de segredo e atualizar todo caller (src/djen_backup/service.py, scripts/canary_check.py, scripts/backfill_probe.py, scripts/drain_unknowns.py, scripts/pipeline/collect.py, scripts/pipeline/run.py) na mesma mudanca para nao quebrar producao, e o arquivo rastreado no repo diverge do script que o proprio deploy gera inline (deployment/DEPLOY_DJEN_V4.sh), entao nao da para validar com confianca qual comportamento de producao um teste estaria protegendo sem arriscar reescrever a fonte de verdade errada. Os dois relays, ao contrario, ja compartilham o mesmo contrato de token X-Relay-Token/RELAY_TOKEN nos dois arquivos rastreados diretamente (sem duplicata divergente em outro script), e ja tem suites de teste dedicadas que este trabalho estende em vez de criar do zero -- material de TDD imediato e de baixo risco. Fechar 2 das 3 superficies com TDD completo e evidencia real e melhor avanco que tentar as 3 e deixar alguma pela metade; o gap fica registrado explicitamente (nao silenciado) para a proxima rodada dedicada ao DJEN proxy Go decidir, com o dono humano se necessario, qual arquivo e a fonte de verdade antes de qualquer mudanca."
---

# Decisao: escopo desta rodada cobre os dois relays, nao o DJEN proxy Go

O DJEN proxy Go (`deployment/djen_proxy.go`) fica como gap explicito
em `next_move`: precisa de decisao previa sobre qual arquivo e a
fonte de verdade de producao (o rastreado no repo ou o gerado inline
por `deployment/DEPLOY_DJEN_V4.sh`) antes de qualquer mudanca de
autenticacao, que e uma mudanca de modelo de seguranca maior que
apertar uma politica ja existente.
