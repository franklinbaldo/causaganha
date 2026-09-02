# TCU — Acórdãos em dados abertos

Estado: **slice mínimo de contrato + aquisição + resolução de URL; download e ingestão de um CSV anual completo ainda pendentes em #984**.

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

## Evidência ao vivo observada (não commitada como fixture de bulk)

Em 2026-09-02, uma requisição real ao manifesto oficial e um range-request no início do CSV de 2026 confirmaram:

- a URL resolvida para o ano 2026 é `.../acordao-completo/acordao-completo-2026.csv`, 275.27 MB conforme o próprio manifesto;
- o cabeçalho real contém todas as colunas de `ingest.REQUIRED_COLUMNS`, mais colunas adicionais (`NUMATA`, `TIPOPROCESSO`, `INTERESSADOS`, `ENTIDADE`, `ADVOGADO`, `QUORUM`, `RECURSOS`, `DECLARACAOVOTO`, `VOTOCOMPLEMENTAR`, `VOTOMINISTROREVISOR`, entre outras) que o produto ainda não usa;
- os bytes são UTF-8 válido — não há bug de encoding em `ingest.load_csv`.

## O que esta etapa ainda não prova

Este slice **não satisfaz sozinho #984**. Antes de ampliar cobertura ou ligar TCU ao MCP/site, ainda é obrigatório:

- baixar pelo menos um CSV anual real (até ~500 MB) usando `acquisition.download_official_csv` com a URL resolvida por `catalog.resolve_acordaos_url`;
- executar o parser da #1002 contra esse arquivo completo e comparar o schema observado com o dicionário linha a linha;
- medir tamanho/custo da expansão histórica (44 anos disponíveis, 1992–2026);
- preservar uma amostra/manifesto de proveniência reproduzível sem commitar um bulk grande no repositório.

Até essa prova ao vivo existir, nenhum dado TCU deve ser anunciado como cobertura do produto.
