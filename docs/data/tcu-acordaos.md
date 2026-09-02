# TCU — Acórdãos em dados abertos

Estado: **contrato, aquisição, resolução de URL e download/ingestão real de um CSV anual completo provados. #984 permanece aberta apenas pela decisão de expor TCU ao MCP/site e pela identidade de anos pré-2017 (ver abaixo).**

O TCU publica sua jurisprudência em dados abertos e documenta a base **Acórdãos** com conjuntos CSV separados por ano. O dicionário oficial declara `KEY` como identificador único do registro e distingue campos de texto primário (`ACORDAO`, `DECISAO`, `RELATORIO`, `VOTO`) da `VISAOGERAL`, que é uma visão simplificada gerada com IA.

A página do portal é renderizada no cliente (os links de download são templates Vue como `{{acordao.arquivo}}`), então a URL anual **não** é resolvida por scraping do HTML. O próprio TCU publica um manifesto oficial estável e pipe-delimited com todos os arquivos disponíveis:

- manifesto de arquivos: <https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/jurisprudencia-arquivos.csv>

Referências oficiais:

- portal: <https://sites.tcu.gov.br/dados-abertos/jurisprudencia/>
- dicionário: <https://sites.tcu.gov.br/dados-abertos/jurisprudencia/dicionario-dados.html>

## Contrato implementado

`src/tcu_acordaos/ingest.py` implementa somente a fronteira determinística depois da aquisição:

1. recebe um CSV local obtido do portal oficial;
2. exige as colunas documentadas usadas pelo produto;
3. usa `KEY` como identidade canônica, sem sintetizar identidade por número/ano/colegiado;
4. rejeita `KEY` ausente ou duplicada;
5. associa a cada registro URL de origem, instante de aquisição e SHA-256 dos bytes de entrada;
6. expõe uma busca literal mínima de TEOR sobre os campos autoritativos;
7. não ingere `VISAOGERAL` como teor primário.

Essa separação é intencional: descoberta de URL, download, retry e publicação são responsabilidades de aquisição e não podem alterar a semântica da transformação.

`src/tcu_acordaos/catalog.py` resolve a URL anual de Acórdãos a partir do manifesto oficial:

1. parseia o CSV pipe-delimited `BASE|ANO|TAMANHO|ARQUIVO` (ignorando a linha de data de geração);
2. filtra pela base `Acórdãos` e pelo ano solicitado;
3. rejeita ano ausente ou ambíguo (múltiplas entradas);
4. valida que a URL resolvida está hospedada em `tcu.gov.br`, reaproveitando a mesma validação de `acquisition.py`.

## Prova ao vivo do bulk real (2026-09-02)

`scripts/tcu_acordaos_prove_bulk.py` foi executado de verdade contra o portal oficial: resolveu a URL de 2026 pelo manifesto, baixou o CSV completo com `acquisition.download_official_csv`, rodou o parser de `ingest.py` sobre o arquivo inteiro, comparou o cabeçalho observado com `REQUIRED_COLUMNS` via `schema_diff.diff_header` e mediu o custo da expansão histórica com `coverage.py`. A evidência completa está em `docs/data/tcu-acordaos-bulk-proof.json` (o CSV bruto de 288 MB não foi commitado):

- URL: `.../acordao-completo/acordao-completo-2026.csv`; 288.646.685 bytes reais (o manifesto declarava um tamanho aproximado, "275.27 MB", medido em época anterior — o arquivo de 2026 ainda está sendo escrito ao longo do ano);
- SHA-256 e `acquired_at` preservados em `tcu-acordaos-bulk-proof.json`;
- **11.791 registros** parseados com sucesso pelo transform de `ingest.py`, cada um com `KEY` única e sem duplicidade;
- schema **compatível**: nenhuma coluna de `REQUIRED_COLUMNS` ausente; 17 colunas extras observadas (`NUMATA`, `TIPOPROCESSO`, `INTERESSADOS`, `ENTIDADE`, `ADVOGADO`, `QUORUM`, `RECURSOS`, `ACORDAOSRELACIONADOS`, `RELATORDELIBERACAORECORRIDA`, `MINISTROREVISOR`, `MINISTROAUTORVOTOVENCEDOR`, `REPRESENTANTEMP`, `UNIDADETECNICA`, `MINISTROALEGOUIMPEDIMENTOSESSAO`, `DECLARACAOVOTO`, `VOTOCOMPLEMENTAR`, `VOTOMINISTROREVISOR`) que o produto ainda não usa — nenhuma foi inventada nem descartada silenciosamente;
- consulta de TEOR de amostra (`"tomada de contas"`) retornou **2.804** acórdãos com proveniência até a URL/SHA-256 do arquivo oficial.

### Dois bugs reais corrigidos por essa prova

Rodar o parser contra dados reais (em vez de fixtures sintéticas em vírgula) expôs dois defeitos que nenhum teste anterior pegava:

1. **Delimitador errado.** `ingest.load_csv` usava o delimitador padrão do `csv.DictReader` (vírgula). O export oficial do TCU é **delimitado por `|`**, com campos entre aspas duplas — confirmado ao vivo em 12 anos amostrados (1992, 1995, 1998, 2000, 2001, 2005, 2009–2026). Com vírgula, o cabeçalho inteiro virava um único campo e **toda** coluna documentada era reportada como ausente — ou seja, o parser nunca funcionou contra um arquivo real do TCU até esta correção.
2. **Limite de tamanho de campo do módulo `csv`.** Campos `VOTO`/`ACORDAO` de acórdãos longos excedem o limite padrão de 128 KiB do `csv` do Python (`_csv.Error: field larger than field limit`), reproduzido ao vivo no arquivo de 2026. `ingest.py` agora eleva o limite para 10 MiB antes de parsear.

Ambos têm teste de regressão em `tests/test_tcu_acordaos_ingest.py` usando fixtures no formato real (pipe-delimitado, aspas duplas, campo grande).

### Achado crítico de identidade: `KEY` não existe antes de 2017

O dicionário oficial declara `KEY` como identificador único, e o contrato de `ingest.canonical_key` depende exclusivamente dele — sem sintetizar identidade a partir de campos de exibição. A prova ao vivo confirmou que **isso só é verdade a partir do arquivo de 2017**:

- **sem `KEY`** (cabeçalho verificado ao vivo em): 1992, 1995, 1998, 2000, 2001, 2005, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016 — nenhum dos 14 anos amostrados nesse intervalo tem `KEY`;
- **com `KEY`** (cabeçalho verificado ao vivo em): 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026 — todos os 10 anos desse intervalo, checados individualmente, têm `KEY`.

Os anos não amostrados diretamente (ex. 1993, 1994, 1996) ficam entre vizinhos confirmados do mesmo lado da fronteira; não foram verificados um a um e não devem ser tratados como confirmados até que sejam.

A transição acontece exatamente entre o arquivo de 2016 e o de 2017. Isso significa que o contrato mínimo de #1002 **só cobre 10 dos 35 anos publicados**. Expandir para 1992–2016 exigiria uma decisão de identidade separada (ex.: `PROC` + `NUMACORDAO` + `ANOACORDAO` como chave composta, com risco de colisão a verificar) — isso **não é parte deste slice** e não deve ser assumido como resolvido.

### Custo/tamanho da expansão histórica

A partir do manifesto oficial completo (`coverage.total_acordaos_size_bytes`, todos os 35 anos 1992–2026):

- **todos os anos publicados**: 35 anos, ≈ 7,39 GiB (7.929.688.229 bytes);
- **apenas os anos compatíveis com o contrato de identidade atual** (2017–2026, `KEY` presente): 10 anos, ≈ 3,85 GiB (4.129.554.432 bytes).

Nenhum desses volumes foi baixado por completo nesta prova — apenas o ano de 2026 (288 MB) foi de fato adquirido e parseado ponta a ponta; o restante é medido a partir dos tamanhos que o próprio manifesto declara.

## O que ainda falta para #984

- decidir e documentar uma estratégia de identidade para 1992–2016 antes de considerá-los elegíveis (ou aceitar explicitamente cobrir só 2017–2026);
- expor TCU no MCP/site permanece **fora de escopo** até essa decisão e até haver revisão de produto sobre limitar a cobertura a 2017+;
- nenhum resumo gerado por IA (`VISAOGERAL`) foi indexado como teor primário — mantido assim.
