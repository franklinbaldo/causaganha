---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-95dnzq-decision-scope-tm02-to-go-proxy"
run_id: "2026-09-25-exciting-mccarthy-95dnzq"
goal_id: "2026-09-25-exciting-mccarthy-95dnzq-goal-djen-proxy-egress-policy"
question: "#1609/TM-02 pede politica minima de egress equivalente em 3 superficies (deployment/relay/function/main.py em Python, deployment/relay-cf/src/index.js em JavaScript/Cloudflare, deployment/djen_proxy.go em Go). Fechar as 3 nesta rodada, ou escopar para uma fatia?"
choice: "Escopar esta rodada para deployment/djen_proxy.go apenas (metodo GET-only + rota /api/-only). O relay Python (deployment/relay/function/main.py) e o relay Cloudflare (deployment/relay-cf/src/index.js) ficam para uma rodada futura."
rationale: "Leitura do codigo real confirmou que djen_proxy.go e a superficie de maior blast radius real: fica sem qualquer autenticacao na frente de comunicaapi.pje.jus.br (o backend de dados que djen-backup de fato consome em producao), aceita todos os metodos HTTP e 4 prefixos de rota amplos incluindo /login, sem prova de necessidade para nenhum deles. Em contraste, deployment/relay-cf (relay Cloudflare) esta documentado em tests/test_archive_cors_proxy_ci_coverage.py e .wisk/knowledge/wiki/continuous-loop-operational-invariants.md como infraestrutura morta, nunca ligada a nenhuma pagina em producao -- corrigi-lo tem valor real menor. O relay Python (deployment/relay/function/main.py) exige token de autenticacao e ja restringe host por allowlist (menor blast radius que o proxy DJEN sem auth nenhuma), mas ainda aceita qualquer metodo HTTP; corrigi-lo direito (metodos, headers Authorization/Cookie, budgets de tamanho) e um segundo trabalho TDD self-contained equivalente em esforco, e uma sessao concorrente desta mesma janela (3zkmxg) ja registrou independentemente que tentar as 3 superficies de #1609 numa unica rodada tende a produzir um fechamento parcial e superficial -- ver reading-okf. Fechar bem uma fatia real e verificavel (com RED->GREEN, CI novo e o bug de source-of-truth do proprio script de deploy corrigido) e melhor do que tocar as 3 superficialmente. #1609 permanece aberta; ver next_move do run.md para o que falta."
---

# Decisao: escopo desta rodada e so djen_proxy.go

`#1609` continua aberta ao final desta rodada -- o relay Python e o
relay Cloudflare (dead infra) nao foram tocados. Ver `next_move` do
`run.md` para o proximo passo natural (relay Python: HTTPS-only,
metodos fechados, stripping de `Authorization`/`Cookie`, budgets de
corpo/resposta -- ja tem suite de teste real em
`tests/deployment/relay/test_main.py` para estender).
