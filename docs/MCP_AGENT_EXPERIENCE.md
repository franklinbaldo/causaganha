# MCP agent experience

O MCP do CausaGanha é a fachada semântica de uma infraestrutura cívica de dados judiciais públicos.

Seu consumidor principal é um agente que quer responder uma pergunta sobre processos, publicações, estado processual ou decisões — não um mantenedor que quer aprender como o repositório armazena Parquet, organiza pipelines ou publica artefatos.

## Regra de ouro

> Um agente deve conseguir escolher e usar a tool correta lendo apenas o catálogo MCP.

Se uma resposta normal exige que o consumidor conheça `indice_processual.parquet`, nomes de itens do Internet Archive, manifests, DuckDB, relações OKF ou a topologia dos coletores, a abstração está vazando.

A infraestrutura continua importante para reproducibilidade, observabilidade e manutenção. Ela não deve ser a linguagem obrigatória da interface de produto.

## Três papéis de evidência

O CausaGanha não deve achatar fontes diferentes em um único “estado do processo”. A fachada expõe três papéis semânticos:

### Arquivo

O que foi publicado ou preservado pelo CausaGanha em um snapshot reproduzível.

Exemplos:

- comunicações DJEN arquivadas;
- capa DataJud presente no snapshot;
- documentos JURIS/STJ incorporados ao acervo;
- `processo_consultar`.

Arquivo pode estar defasado em relação ao processo real. A data do dataset faz parte da evidência.

### Estado

O que a fonte oficial registra agora sobre a trajetória processual: movimentos, graus e marco mais recente conhecido.

A superfície pretendida é uma consulta DataJud live por CNJ (`datajud_processo` / `processo_estado`). Estado não é teor: um movimento “Sentença” prova que o evento foi registrado, não o conteúdo da sentença.

### Teor

O conteúdo efetivo de decisões ou documentos quando uma fonte de texto o fornece.

JURIS/STJ e documentos associados são superfícies de teor. Não reconstruir o fundamento de uma decisão a partir de movimentos ou metadados DataJud.

## Tools de produto e tools de operação

### Produto

Estas devem dominar a experiência de um agente comum:

- `processo_consultar(cnj)` — “o que o acervo sabe sobre este processo?”;
- `datajud_processo(cnj, tribunal?)` — “o que aconteceu mais recentemente?” (planejada em #890);
- `publicacoes_buscar(...)` — “quais publicações correspondem a este CNJ/OAB/parte/texto?”;
- uma superfície de teor (`decisoes_buscar` ou equivalente) — “há decisão/acórdão e o que ele diz?”;
- cobertura contextual quando uma ausência precisa ser qualificada.

Os nomes e docstrings devem falar no vocabulário dessas perguntas, não no vocabulário do pipeline.

### Operação

`causaganha_status`, `datajud_status`, `djen_backup_status`, `tjro_juris_status` e `stj_acordaos_status` continuam úteis para diagnóstico e manutenção.

Um agente não precisa chamá-las antes de uma consulta normal. Elas são a superfície de observabilidade, não o índice da API.

## Contrato de saída

Resultados de produto devem carregar informação suficiente para o agente responder sem fazer joins mentais de infraestrutura.

Campos semânticos preferidos, quando aplicáveis:

- `resumo` — síntese factual curta do que a tool encontrou;
- blocos/evidências por fonte;
- `natureza` — `arquivo`, `estado` ou `teor`;
- `fonte_oficial` ou origem inteligível;
- timestamp de observação/geração;
- `limitacoes` — por que uma ausência ou defasagem muda a inferência;
- `next_actions` — próximas consultas semanticamente úteis;
- URL pública quando houver uma superfície humana equivalente.

Detalhes de transporte como `parquet_ia`, `manifest_local`, `loaded_local` e `loaded_remote` não devem ser necessários para interpretar uma resposta. Quando forem úteis para diagnóstico, pertencem a campos explicitamente operacionais ou às tools de status.

## Next actions

`next_actions` é parte da agent experience, não decoração.

Exemplos:

- snapshot encontrado, mas a pergunta pede atualidade → consultar estado live;
- movimento encontrado, mas a pergunta pede fundamento → buscar teor;
- processo não aparece no snapshot → verificar cobertura/freshness e, quando possível, consultar fonte live;
- documentos foram truncados → buscar continuação em vez de inferir que a lista é completa.

A action deve dizer **quando** é útil e apontar para uma tool existente. Não anunciar tools inexistentes como se já estivessem disponíveis.

## Erros e ausência

A fachada deve preservar quatro estados diferentes:

1. input inválido;
2. fonte/serviço indisponível;
3. consulta válida sem registro;
4. cobertura insuficiente para tratar a ausência como evidência forte.

Erro de transporte não vira “não encontrado”. Ausência em um snapshot não vira “o processo não existe”.

## Critério de teste

Além de testes de schema e serviço, a superfície MCP deve ser testada como um catálogo que um agente vê.

Cenários mínimos:

- “o que sabemos sobre este CNJ?” seleciona `processo_consultar` sem status prévio;
- “qual o último andamento?” não é respondido pelo snapshot quando a tool de estado existir;
- “o que a decisão diz?” não é respondido apenas por movimento DataJud;
- ausência em fonte incompleta produz limitação/next action;
- uma pessoa sem conhecimento do repo consegue explicar a diferença entre as tools a partir das descrições.

## Compatibilidade

A migração é incremental. Campos operacionais e tools antigas não precisam ser removidos de uma vez. A prioridade é construir uma camada semântica estável por cima, marcar claramente o que é diagnóstico e só depois avaliar deprecações.

Relacionado a #914, #890, #891 e #892.
