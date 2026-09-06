---
type: AgentGoal
id: "2026-09-06-exciting-mccarthy-yigsua-goal-fix-1197-query-error-classification"
run_id: "2026-09-06-exciting-mccarthy-yigsua"
goal: "Fazer runQuery() em DuckDBExplorer.svelte parar de classificar falhas HTTP transitórias (5xx, timeout, rede) durante a execução da consulta como 'dataset não encontrado', preservando a classificação correta apenas para erros inequivocamente compatíveis com arquivo remoto inexistente (404 + referência ao itemId), sem decorar erros SQL locais não relacionados à fonte, por issue #1197."
rationale: "A rodada sk8ec6 corrigiu a validação de disponibilidade do dataset em DuckDBExplorer.svelte (#1193/PR #1195), mas o mesmo erro semântico continua na execução da consulta: `runQuery()` decora qualquer erro cuja mensagem contenha 'HTTP' (ou o itemId, presente em toda URL) com o texto de 'dataset não encontrado', mesmo quando a causa real é um 5xx, timeout ou falha de rede durante a leitura remota do Parquet. #1197 foi aberta pelo próprio dono minutos antes desta rodada, marcada 'READY para IMPLEMENTAÇÃO', escopo pequeno e único (o catch de runQuery()), e a #1132 já declara depender dela para não ampliar uma semântica de erro ainda inconsistente."
success_signal: "Testes RED cobrindo (a) erro HTTP/5xx/timeout/rede transitório durante conn.query() não produz o texto 'não encontrado no Internet Archive'; (b) erro inequivocamente compatível com arquivo remoto inexistente (404 + itemId) ainda produz esse texto, sem esconder a mensagem original; (c) erro SQL local (sintaxe) não é decorado com nenhum dos dois textos; (d) seleção de tribunal/ano e SQL digitado sobrevivem ao erro transitório; (e) nova execução após erro transitório pode ter sucesso sem reload — viram GREEN após a implementação, sem regressão nos testes existentes de #1193 nem no restante da suíte web (`npx vitest run` completo) e sem regressão nos gates Python (`ruff check`/`ruff format --check`/`pytest -q`, embora nenhum arquivo Python de produção deva mudar). PR aberta e mesclada."
status: "achieved"
---

# Goal — corrigir classificação de erro em runQuery() (#1197)

Fechar o mesmo erro semântico que `#1193` já corrigiu na validação do dataset, mas agora no caminho de execução da consulta (`runQuery()`), seguindo TDD: testes RED expressando o comportamento desejado, implementação mínima, GREEN, PR.
