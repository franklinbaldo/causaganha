# TCU — Acórdãos em dados abertos

Estado: **slice mínimo de contrato; aquisição bulk real ainda pendente em #984**.

O TCU publica sua jurisprudência em dados abertos e documenta a base **Acórdãos** com conjuntos CSV separados por ano. O dicionário oficial declara `KEY` como identificador único do registro e distingue campos de texto primário (`ACORDAO`, `DECISAO`, `RELATORIO`, `VOTO`) da `VISAOGERAL`, que é uma visão simplificada gerada com IA.

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

## O que esta etapa ainda não prova

Este slice **não satisfaz sozinho #984**. Antes de ampliar cobertura ou ligar TCU ao MCP/site, ainda é obrigatório:

- resolver uma URL anual real a partir do portal oficial sem scraping frágil;
- baixar pelo menos um CSV anual real;
- registrar URL, data de aquisição, tamanho e SHA-256 observados;
- executar o parser contra esse arquivo e comparar o schema observado com o dicionário;
- medir tamanho/custo da expansão histórica;
- preservar uma amostra/manifesto de proveniência reproduzível sem commitar um bulk grande no repositório.

Até essa prova ao vivo existir, nenhum dado TCU deve ser anunciado como cobertura do produto.
