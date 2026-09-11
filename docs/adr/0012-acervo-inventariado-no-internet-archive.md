# ADR 0012 — Inventariar o acervo no Internet Archive e publicar sem bloqueio nacional

Data: 2026-09-11

Status: consolidação de decisões anteriores, com implementação parcial existente; integração operacional e reprocessamento pendentes.

Atualização: a [integração operacional por tribunal/ano](../planning/archive-consolidation-rollout.md) foi implementada e validada localmente. A ativação do workflow, publicação do backlog e prova na homepage continuam pendentes. O documento registra comandos de operação e limites de publicação.

## Antecedentes e implementação existente

Esta estratégia não começa nesta ADR:

- [Plano de consolidação, 02/06/2026](../planning/consolidation-plan.md), §§2.1 do backfill e 4.3: descobrir datas com ZIPs sem Parquets, manter o IA como fonte de verdade e o dashboard como projeção. O §0.2 já alerta que o workflow usa o script legado, enquanto existe outro caminho refatorado.
- [Fonte da verdade do manifesto, 01/06/2026](../planning/manifest-source-of-truth.md), §4: eventos imutáveis no Archive e compactação para reconstruir o estado da coleta; o documento registra a Fase 3 concluída em julho. Não é uma proposta nova de log.
- [Plano de otimização de Parquets, 07/06/2026](../planning/parquet-storage-optimization-plan.md): descreve consolidação por tribunal/ano e identifica que marcadores de versão podem impedir reprocessamento de dados já publicados.
- [Contrato do catálogo](../CATALOG.md): catálogo SQL reconstruível sobre Parquets públicos em itens por tribunal/ano.

No código, `scripts/generate_catalog.py` já inventaria metadata do Archive e `scripts/pipeline/consolidate.py` já oferece `consolidate_tribunal_year` via `--tribunal` e `--year`. Porém, o workflow `consolidate-parquet.yml` continua chamando o modo diário `--backfill`, com a exigência de completude nacional observada na investigação.

A ADR explicita o requisito de não bloquear dados disponíveis por pendências de outros tribunais e reúne os critérios para fechar essa integração. Deve-se aproveitar os módulos existentes, não construir um pipeline paralelo. Documentos antigos descrevem intenções e partes implementadas; não constituem prova de rollout completo.

## Decisão

O Internet Archive é a fonte de verdade sobre os arquivos preservados. O manifesto de arquivos deve ser reconstruível pelas APIs do Archive: descoberta dos itens, inventário pela API de metadata e validação de leitura dos artefatos. Checkpoints e o manifesto de coleta podem acelerar o trabalho, mas não devem ser a única forma de descobrir o acervo.

**Todo ZIP válido já preservado deve poder chegar à busca sem esperar que todos os tribunais de uma data estejam completos.** Consolidar por tribunal e partição, publicar os Parquets disponíveis e informar a cobertura parcial. Uma falha deve ficar restrita à unidade afetada.

O produto é o acesso duradouro aos dados: consulta no site, download e reutilização. MCP e CLI são interfaces complementares.

## Arquivos e verificações têm significados diferentes

| Evidência | Conclusão permitida |
|---|---|
| ZIP listado e validado | Arquivo preservado para o tribunal/data |
| Parquet publicado e validado | Dados estruturados disponíveis; a busca ainda depende da inclusão no índice |
| Nenhum ZIP encontrado | Lacuna no inventário observado; não prova ausência de publicação |
| Registro de consulta ao DJEN sem publicação | Ausência observada naquela verificação |
| Registro de erro | Tentativa falhou; não equivale a ausência |
| Nenhum registro de verificação | Estado desconhecido; candidato à consulta |

Falhas na API do Archive não provam remoção de arquivos. Um inventário incompleto deve manter essa condição explícita e não apagar silenciosamente evidências anteriores. Pares tribunal/data sem ZIP formam uma fila de investigação, sem bloquear os arquivos existentes.

## Acompanhamento da coleta reconstruível

Preservar também registros de verificação no Archive, aproveitando o log de eventos existente: tribunal, data de referência, instante da tentativa, resultado interpretado, evidência da resposta e versão do coletor. Credenciais não pertencem a esses registros.

O estado da coleta deve ser uma projeção reconstruível desses registros. `sync-manifest.parquet` continua sendo sua representação operacional atual; não é prova suficiente da existência física de um arquivo e não deve ser uma barreira para consolidar o acervo disponível.

HTTP 200 sozinho não prova publicação; erro de rede ou HTTP 403 não prova ausência. As regras de interpretação do DJEN continuam válidas.

## Fluxo pretendido

1. Descobrir itens no Archive e inventariar ZIPs e Parquets: URL, tamanho, checksum quando disponível e instante da observação.
2. Validar e converter os ZIPs por tribunal/partição. Registrar quais entradas e qual versão da transformação produziram cada saída.
3. Publicar e verificar a leitura dos Parquets antes de promovê-los no catálogo.
4. Atualizar o índice processual pelos Parquets publicados e verificar a consulta no site.
5. Reprocessar a partição quando surgirem ZIPs novos ou alterados. Um marcador de conclusão não pode congelar uma partição parcial para sempre.
6. Mostrar separadamente cobertura preservada, convertida e pesquisável, com suas datas. Geração recente do índice não implica dados recentes ou cobertura completa.

As etapas devem ser repetíveis sem duplicar registros. Falhas e lacunas precisam aparecer nas métricas e no resultado operacional, mesmo quando outras partições avançam.

## Motivo e evidência

Na [execução de 11/09/2026](https://github.com/franklinbaldo/causaganha/actions/runs/34597409357), o consolidador pulou 04/09/2026 com `expected=96 missing=31 present=65`. O manifesto de coleta consultado na investigação registrava 65 tribunais com upload e 31 sem publicação. O código priorizava o catálogo de arquivos e não combinava esses registros de ausência.

O CNJ `7008332-16.2026.8.22.0007` estava no [ZIP do TJRO de 04/09/2026](https://archive.org/download/djen-tjro-2026/djen-2026-09-04-TJRO.zip), mas não no índice consultado pela homepage. Preservação e disponibilidade para busca são etapas distintas.

## Critérios de entrega

- Implementar descoberta independente pelo Archive e remover a exigência de completude nacional para publicar partições disponíveis.
- Integrar a consolidação por tribunal/partição ao workflow, catálogo e índice; sua existência no CLI não conclui a migração.
- Verificar que um tribunal pendente não bloqueia outro, que lacunas não viram “sem publicação”, que falhas de inventário não removem arquivos e que novos ZIPs entram em partições já publicadas.
- Recuperar o backlog, começando pelo TJRO 2026, e localizar o CNJ acima na homepage com proveniência para os dados preservados.
- Tornar observáveis falhas parciais, arquivos ainda não indexados e cobertura de cada etapa.

Esta decisão não afirma que o pipeline foi corrigido, que o backlog foi processado ou que novos dados foram publicados.
