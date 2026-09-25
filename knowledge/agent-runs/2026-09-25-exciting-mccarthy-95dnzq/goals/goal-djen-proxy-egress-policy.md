---
type: AgentGoal
id: "2026-09-25-exciting-mccarthy-95dnzq-goal-djen-proxy-egress-policy"
run_id: "2026-09-25-exciting-mccarthy-95dnzq"
goal: "Estreitar deployment/djen_proxy.go (TM-02, issue #1609) para o menor egress que o produto real precisa: apenas metodo GET e apenas o prefixo de rota /api/, removendo /login, /swagger/ e o /comunicacao solto sem prova de necessidade -- e garantir que essa correcao sobreviva ao proximo deploy real, nao apenas ao arquivo tocado nesta rodada."
rationale: "djen_proxy.go fica sem autenticacao na frente de comunicaapi.pje.jus.br (o backend real de dados que src/djen_backup/djen.py e web/src/lib/djenClient.ts consomem) e hoje aceita qualquer metodo HTTP e 4 prefixos de rota amplos, incluindo /login -- exatamente o padrao que TM-02 descreve como podendo virar WAF-bypass, consumo de capacidade upstream ou alcance de rotas desnecessarias. Evidencia ao vivo (nao suposicao): o proprio comentario de web/src/lib/djenClient.ts ja documentava que todos os 7 endpoints do spec (openapi/djen.yml) ficam sob /api/v1/, e src/djen_backup/djen.py so chama request_with_retry(client, 'GET', ...) -- nunca outro metodo. Isso prova, sem precisar adivinhar, que /login, /swagger/ e /comunicacao solto nunca sao exercitados por nenhum caminho de produto real, e que metodos alem de GET tambem nao. Alem disso, deployment/DEPLOY_DJEN_V4.sh reescrevia djen_proxy.go via heredoc toda vez que era executado -- rodar esse script de deploy sem tocar nele primeiro apagaria silenciosamente qualquer correcao feita so no arquivo rastreado, tornando a correcao de seguranca cosmetica."
success_signal: "Um novo teste Go (deployment/djen_proxy_test.go, deployment/go.mod, sem infraestrutura de teste previa para este arquivo) prova, via httptest contra o handler real: (1) allowed('/login')/('/swagger/...')/('/comunicacao') retornam false; (2) POST/PUT/DELETE/PATCH/OPTIONS numa rota permitida retornam 405, mesmo antes de qualquer checagem de rota; (3) GET numa rota /api/ permitida continua chegando ao proxy real (200). O teste falha (RED) contra o conteudo original do arquivo (confirmado ao vivo antes de qualquer mudanca) e passa (GREEN) depois. deployment/DEPLOY_DJEN_V4.sh para de reescrever djen_proxy.go/Dockerfile via heredoc -- passa a construir a partir dos arquivos ja rastreados no diretorio, eliminando o risco de reverter a correcao no proximo deploy real. Uma nova job no CI (.github/workflows/test.yml) roda go vet/go test/go build sobre deployment/ a cada PR, para que uma regressao futura nesse arquivo nao passe despercebida (mesmo padrao ja estabelecido para deployment/archive-cors-proxy). O comentario desatualizado em web/src/lib/djenClient.ts (que ainda documentava /swagger/, /comunicacao e /login como parte do whitelist) e corrigido. ruff/pytest/okf-parser continuam verdes."
status: "achieved"
---

# Objetivo: estreitar egress do djen_proxy.go (TM-02, #1609)

Trabalho principal desta rodada. `#1609` cobre 3 superficies
heterogeneas (relay Python, relay Cloudflare, `djen_proxy.go` em Go);
esta rodada escopa deliberadamente para a fatia de maior risco real —
`djen_proxy.go`, que fica sem autenticacao na frente do backend real de
dados do produto — deixando as outras duas para uma rodada futura (ver
`decision-scope-tm02-to-go-proxy` e `next_move` do `run.md`). Ver
`decision-fix-deploy-script-drift` para o porque a correcao precisou
tocar tambem o script de deploy, nao so o arquivo Go.
