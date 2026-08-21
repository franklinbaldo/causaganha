# Modelo de produto do CausaGanha

Este documento fixa a linguagem de produto usada pelo README e pelas superfícies públicas. Ele não substitui os contratos físicos de dados, RFCs nem a documentação operacional.

## Tese

O CausaGanha é uma camada pública e verificável para acompanhar o rastro de processos judiciais brasileiros. Ele preserva publicações, reconcilia fontes oficiais e mantém explícita a proveniência de cada fato.

A unidade de confiança do produto não é “uma resposta unificada”. É uma resposta em que o consumidor consegue saber **qual fonte sustenta qual proposição e de quando é aquela evidência**.

## Três tipos de evidência

### Arquivo

Responde: **o que foi publicado e preservado?**

A fundação é o DJEN arquivado no Internet Archive. O arquivo mantém ZIPs originais, estado de cobertura e derivados públicos reconstruíveis.

Um arquivo é um snapshot preservado. Sua ausência de novidade não prova, por si só, que o processo não teve andamento posterior.

### Estado

Responde: **onde o processo está e o que aconteceu na linha processual?**

DataJud é a principal fonte oficial de metadata/movimentação. Movimento prova que determinado evento foi registrado; não prova o fundamento ou o conteúdo integral do ato correspondente.

### Teor

Responde: **o que a decisão ou documento efetivamente diz?**

Quando disponíveis, JURIS e STJ fornecem documentos/decisões usados como evidência textual. Teor não deve ser reconstruído a partir do nome de um movimento DataJud.

## Regra central

```text
arquivo ≠ estado ≠ teor
```

As três dimensões podem ser compostas, mas não fundidas sem proveniência.

Exemplo de formulação correta:

> O DataJud registra julgamento em determinada data; o documento de jurisprudência correspondente contém a fundamentação X.

Formulação inadequada:

> O DataJud decidiu X por causa de Y.

O segundo enunciado transforma metadata em teor.

## Quatro fontes

### DJEN

- natureza: comunicações judiciais;
- papel: preservação, busca e cobertura histórica;
- artefatos: ZIPs, Parquets, `sync-manifest.parquet`, catálogo;
- não implica: inteiro teor de toda decisão nem estado processual live completo.

### TJRO JURIS

- natureza: jurisprudência/documentos do TJRO;
- papel: teor estruturado e corpus de decisões;
- não implica: cobertura de todo processo ou disponibilidade live permanente.

### STJ Acórdãos

- natureza: acórdãos do STJ;
- papel: decisões do STJ e reconciliação por processo;
- não implica: trajetória processual completa fora do STJ.

### DataJud

- natureza: metadata e movimentação processual;
- papel: capa, classe, assunto, órgão, grau, datas, movimentos e facetas;
- não implica: ratio, fundamento ou conteúdo integral do ato.

## Processo como recurso

`indice_processual.parquet` é um índice fino, não uma tabela universal de conteúdo. Para um CNJ ele identifica as fontes e arquivos de origem que possuem registros. Os consumidores então consultam esses Parquets diretamente.

Isso preserva três propriedades:

1. a fonte física continua identificável;
2. não se cria uma cópia larga e divergente de todos os campos;
3. falha de uma fonte pode ser representada como lacuna parcial, sem apagar as demais.

## Superfícies

### Site

Interface humana para consulta por CNJ, pesquisa de publicações, cobertura e exploração dos dados.

### Dados públicos

Interface reproduzível para pesquisadores, jornalistas, legaltechs e outros consumidores. O catálogo é distribuído como SQL auditável, materializado pelo próprio consumidor em DuckDB.

### MCP

Interface read-only orientada a agentes. Tools devem explicitar quando leem estado local, artefato publicado ou fonte live. Ingestão, upload e backfill permanecem fora da superfície MCP.

## Proveniência e freshness

Toda resposta que dependa de estado temporal deve distinguir, quando aplicável:

- quando o dataset foi gerado;
- quando a fonte foi consultada;
- quais fontes estavam carregadas;
- quais fontes têm registro para aquele processo;
- indisponibilidade de fonte versus ausência de registro.

“Não encontrei” só é equivalente a “não existe” quando o contrato da fonte e a cobertura observada permitem essa conclusão.

## Produto suportado e Lab

A camada suportada é o arquivo público e as superfícies verificáveis construídas sobre fontes oficiais e artefatos reproduzíveis.

O Lab contém classificação, embeddings, segmentação, modelos e experimentos derivados. Resultados analíticos podem ser úteis, mas não recebem automaticamente o mesmo status epistêmico de um registro oficial.

## Regra editorial

Ao descrever o CausaGanha publicamente:

- começar pelo trabalho que a pessoa consegue realizar;
- tratar o DJEN como fundação de preservação, não como definição exclusiva do produto;
- mostrar fontes como papéis complementares, não como logos equivalentes;
- não transformar pipeline existente em promessa de cobertura completa;
- apresentar lacunas e freshness como parte da qualidade do produto;
- preservar a distinção entre fato oficial, artefato derivado e inferência experimental.
