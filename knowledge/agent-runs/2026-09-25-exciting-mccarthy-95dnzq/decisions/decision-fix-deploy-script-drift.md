---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-95dnzq-decision-fix-deploy-script-drift"
run_id: "2026-09-25-exciting-mccarthy-95dnzq"
goal_id: "2026-09-25-exciting-mccarthy-95dnzq-goal-djen-proxy-egress-policy"
question: "deployment/DEPLOY_DJEN_V4.sh reescrevia djen_proxy.go e Dockerfile inteiros via heredoc toda vez que era executado, com um conteudo ligeiramente diferente (e mais antigo, sem a correcao de seguranca) do arquivo rastreado deployment/djen_proxy.go. Corrigir so o arquivo rastreado (superficial, teatral) ou tambem consertar o script de deploy?"
choice: "Consertar tambem o script de deploy: DEPLOY_DJEN_V4.sh para de embutir uma copia duplicada do codigo Go/Dockerfile via heredoc e passa a construir a partir dos arquivos ja rastreados no diretorio (deployment/djen_proxy.go, deployment/go.mod, deployment/Dockerfile, este ultimo extraido do heredoc para um arquivo proprio)."
rationale: "Se a proxima pessoa (ou automacao) rodar deployment/DEPLOY_DJEN_V4.sh sem saber que o heredoc existia, o comando 'cat > djen_proxy.go << GO' sobrescreveria silenciosamente a correcao de seguranca desta rodada com a versao antiga (WHITELIST de 4 prefixos incluindo /login, sem restricao de metodo) antes mesmo do 'gcloud run deploy --source .' rodar -- a mudanca em djen_proxy.go teria zero efeito na proxima implantacao real. Isso e exatamente o tipo de 'ambiente com autoridade de deploy' que CLAUDE.md/docs/SECURITY_THREAT_MODEL.md tratam como ativo critico (TM-10/TM-15): um artefato de seguranca so vale alguma coisa se sobrevive ao pipeline que realmente publica o codigo. A copia embutida no heredoc tambem tinha funcionalidades (graceful shutdown, http.Server estruturado) que a copia rastreada nao tinha -- as duas ja haviam divergido antes desta rodada, o que e por si so um sinal de que duas fontes da verdade para o mesmo arquivo sao um erro de arquitetura, nao so um detalhe de deploy. A correcao escolhida elimina a duplicacao (fonte unica = arquivos rastreados), sem tentar tambem re-adicionar o graceful shutdown como funcionalidade nesta mesma mudanca -- misturar as duas coisas aumentaria o escopo e o risco de uma PR de seguranca sem necessidade; se o graceful shutdown ainda for desejado, e um pedido de feature separado e explicito, nao algo reintroduzido de contrabando por um heredoc nao rastreado."
---

# Decisao: eliminar a duplicacao fonte-da-verdade no script de deploy

`DEPLOY_DJEN_V4.sh` agora roda `go test ./...` antes de fazer qualquer
delete/deploy e constroi a partir dos arquivos ja versionados
(`djen_proxy.go`, `go.mod`, `Dockerfile`) em vez de regeneralos.
Registrado tambem como achado explicito: a versao antiga do heredoc
tinha graceful shutdown que o arquivo rastreado nao tinha -- isso foi
descartado deliberadamente desta mudanca (ver `rationale`), nao
esquecido.
