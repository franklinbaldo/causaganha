---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-yigsua-decision-classification-heuristic"
run_id: "2026-09-06-exciting-mccarthy-yigsua"
goal_id: "2026-09-06-exciting-mccarthy-yigsua-goal-fix-1197-query-error-classification"
question: "Como classificar o erro capturado no catch de runQuery() sem repetir o defeito antigo (message.includes(itemId) || message.includes('HTTP')), que confundia qualquer erro HTTP com ausência do dataset?"
choice: "Função pura classifyQueryError(message, itemId) com três saídas: 'missing' apenas quando a mensagem referencia o itemId selecionado E contém um sinal inequívoco de ausência (código 404 ou 'not found'); 'unavailable' quando contém sinais de falha HTTP genérica/5xx/timeout/rede (mas sem o par itemId+404/not-found); e null (mensagem exibida como está, sem decoração) em qualquer outro caso — cobrindo erros SQL locais (sintaxe, coluna inexistente, etc). Reaproveitar describeMissingDataset()/describeUnavailableDataset() já existentes de #1193 em vez de criar um terceiro texto."
rationale: "A condição antiga usava OR: bastava a mensagem mencionar a URL (que sempre contém o itemId) OU a palavra 'HTTP' para virar 'dataset ausente' — e mensagens de erro httpfs de 5xx/timeout quase sempre contêm ambos. Exigir itemId E um sinal de 404/not-found reduz o classificador a exatamente o caso inequívoco que a #1197 pede, sem introduzir um terceiro vocabulário de mensagens (reduz o risco de 'esconder erro SQL legítimo sob mensagem genérica', apontado como risco na própria issue). Retornar null para o caso não classificado evita decorar erros de SQL locais, que também podem conter a palavra 'not found' (ex. 'Binder Error: column ... not found') mas nunca mencionam o itemId do dataset."
---

# Decisão — heurística de classificação de erro em runQuery()

`missing` exige itemId + sinal 404/not-found; `unavailable` cobre HTTP/5xx/timeout/rede sem esse par; qualquer outro erro (incluindo erro SQL local que contenha "not found" sem o itemId) passa sem decoração. Reaproveita os textos já existentes de `#1193` em vez de criar um terceiro.
