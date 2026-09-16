---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-96cgqx-decision-follow-scheduled-scaffold-and-select-1050"
run_id: "2026-09-16-exciting-mccarthy-96cgqx"
question: "Qual issue de dominio trabalhar nesta rodada, dado que o prompt agendado instrui o scaffold AgentRun legado (em tensao com a politica de deprecacao de knowledge/agent-runs/index.md e .claude/hourly-loop.md) e que ha multiplas candidatas abertas (#1050, #1482, #1468-1472, #1093)?"
choice: "Seguir o scaffold AgentRun desta sessao agendada e selecionar #1050 (13o lote real multi-tribunal do corpus do segmentador) como trabalho de dominio da rodada, em vez de #1482 (deploy de infraestrutura Cloudflare) ou da cadeia Parquet/CNJ #1468-1472."
rationale: "(1) O prompt desta sessao agendada instrui literal e explicitamente o scaffold legado como primeira acao obrigatoria; o proprio system-reminder desta sessao declara que instrucoes de usuario/scaffold sobrescrevem comportamento padrao, e cinco rodadas anteriores (to0ars, bueov4, ez5wkn, 6kxfkh, zrek2s) ja resolveram a mesma tensao AgentRun-vs-Wisk da mesma forma, sem fato novo que justifique reabrir. (2) Entre as opcoes de trabalho de dominio investigadas, #1050 e a unica com avanco real, mensuravel (document_count, val/test ceiling) e inteiramente verificavel localmente (pytest, ruff, okf-parser, scripts/segmenter_governance_status.py) sem depender de credenciais externas. (3) #1482 ja tem toda a mitigacao de aplicacao implementada e testada; o unico avanco restante e um deploy real de Cloudflare Worker com CLOUDFLARE_API_TOKEN, que esta sessao nao possui -- executar isso seria uma acao de infraestrutura de producao hard-to-reverse/visivel para terceiros sem confirmacao humana disponivel nesta sessao agendada, e sem credenciais o resultado nao seria verificavel (nenhum GREEN real possivel). (4) A cadeia Parquet/CNJ #1468-1472 e um epico de alto risco (regeneracao de dataset publicado) historicamente bloqueado por falta de credenciais IA em rodadas anteriores -- mesmo problema de nao-verificabilidade nesta sessao. Alternativas descartadas: #1482 (deploy real sem credenciais/confirmacao humana), #1468-1472 (historico de bloqueio por credenciais IA + alto risco em dataset publicado), #1093 (a propria issue se declara nao-prioritaria agora). PR #1563 de sessao concorrente ja estava com CI verde e foi mesclada por terceiros durante a leitura desta rodada, sem necessidade de acao minha."
---

# Decisao: scaffold AgentRun + selecao de #1050

Ver `reference` e `reasoning` no frontmatter. Nenhum fato novo nesta
rodada muda a resolucao ja estabelecida por cinco decisoes anteriores
sobre a tensao AgentRun-vs-Wisk; a decisao aqui e principalmente sobre
qual issue de dominio trabalhar, dado o estado real do repositorio
verificado nas leituras desta rodada.
