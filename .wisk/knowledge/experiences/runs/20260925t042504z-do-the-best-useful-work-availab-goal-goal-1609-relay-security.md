---
goal: "Fechar a fatia Python + CF do relay em #1609/TM-02: relay Python (deployment/relay/function/main.py) e CF relay (deployment/relay-cf/src/index.js) compartilhando a mesma politica minima de egress -- HTTPS-only, metodo GET/HEAD/POST, stripping explicito de Authorization/Cookie -- e o relay Python (superficie de producao real) com budgets de tamanho de request/resposta."
id: "run-goals/20260925t042504z-do-the-best-useful-work-availab/goal-1609-relay-security"
kind: "task-advance"
rationale: "docs/SECURITY_THREAT_MODEL.md/TM-02 e a propria issue #1609 ja apontavam essa lacuna exata (Python relay aceita metodo amplo e nao strippa Authorization/Cookie; CF relay tem a mesma lacuna de headers). O relay Python e a superficie realmente usada em producao (STJ/TJRO/TSE sync workflows); um token vazado hoje podia emitir qualquer metodo HTTP e carregar Authorization/Cookie de quem chamou ate o tribunal de destino, e um upstream/chamador mal-configurado nao tinha nenhum teto de tamanho de request/resposta."
run: "runs/20260925T042504Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "tests/deployment/relay/test_main.py com 8 testes novos RED->GREEN (scheme http rejeitado 403, metodos PUT/PATCH/DELETE/OPTIONS rejeitados 405, GET/HEAD/POST aceitos, Authorization/Cookie nao encaminhados, request >5MiB rejeitado 413, resposta >50MiB abortada 502 durante streaming) e a suite inteira do modulo (41/41) verde; deployment/relay-cf/test/index.test.js com 1 teste novo RED->GREEN (Authorization/Cookie nao encaminhados) e a suite inteira (10/10) verde; docs/SECURITY_THREAT_MODEL.md/TM-02 e deployment/relay/README.md atualizados para refletir o estado real."
type: "RunGoal"
---

# RunGoal
