# Relatório de Experimentos: Judicial Multi-Algorithm NER

Avaliação empírica em CPU na base real do DJEN (`ia_expanded_decisions.parquet`).

## 1. Latência e Throughput por Algoritmo Especializado (1 Core CPU)

| Extrator / Algoritmo | Throughput (doc/s) | Média (ms) | p95 (ms) | Entidades Extraídas |
| :--- | :--- | :--- | :--- | :--- |
| **1. CNJ (Regex + Modulo 97)** | 13840.0 | 0.07 | 0.22 | 654 |
| **2. Normas (Parser Léxico + Anáfora)** | 3434.1 | 0.29 | 1.30 | 1550 |
| **3. Valores (Moeda, % e Papel)** | 7366.5 | 0.14 | 0.42 | 516 |
| **4. Datas (Prazos e ISO)** | 4438.9 | 0.22 | 0.70 | 1313 |
| **5. Organizações (Grandes Litigantes)** | 822.3 | 1.22 | 3.66 | 1300 |
| **6. PIPELINE COMPOSTO SECCIONAL** | 527.0 | 1.90 | 6.36 | 4548 |

## 2. Indicadores de Precisão Mecânica e Resolução

- **Números CNJ**: 654 detectados, com **100.0% validados com sucesso pelo algoritmo Módulo 97 da Res. 65/2008**.
- **Referências Normativas**: 1550 citações identificadas. Top diplomas: `CPC` (854), `PENDENTE_CONTEXTO` (425), `LEI_9099_JUIZADOS` (42), `CP` (33).
- **Valores Financeiros**: 516 quantias distribuídas entre condenações de mérito, valor da causa, astreintes e percentuais de sucumbência.
- **Grandes Litigantes**: 1300 ocorrências mapeadas diretamente aos identificadores canônicos do CNJ.

## 3. Amostra de Documento Anotado com Grafo Seccional

```json
// Decisão analisada: 10 entidades extraídas nas seções
[
  {
    "literal": "ESTADO DE RONDÔNIA",
    "start": 40,
    "end": 58,
    "char_count": 18,
    "section": "CABECALHO",
    "entity_type": "ORGANIZACAO",
    "normalized_value": {
      "canonical_name": "ESTADO_DE_RONDONIA",
      "catalog_role": "ORGAO_PUBLICO"
    },
    "role": "ORGAO_PUBLICO",
    "confidence": 0.99,
    "evidence": "Grande litigante do catálogo CNJ identificado em CABECALHO"
  },
  {
    "literal": "BANCO DO BRASIL",
    "start": 147,
    "end": 162,
    "char_count": 15,
    "section": "RELATORIO",
    "entity_type": "ORGANIZACAO",
    "normalized_value": {
      "canonical_name": "BANCO_DO_BRASIL_SA",
      "catalog_role": "INSTITUICAO_FINANCEIRA"
    },
    "role": "INSTITUICAO_FINANCEIRA",
    "confidence": 0.99,
    "evidence": "Grande litigante do catálogo CNJ identificado em RELATORIO"
  },
  {
    "literal": "BANCO DO BRASIL S/A",
    "start": 328,
    "end": 347,
    "char_count": 19,
    "section": "RELATORIO",
    "entity_type": "ORGANIZACAO",
    "normalized_value": {
      "canonical_name": "BANCO_DO_BRASIL_SA",
      "catalog_role": "INSTITUICAO_FINANCEIRA"
    },
    "role": "INSTITUICAO_FINANCEIRA",
    "confidence": 0.99,
    "evidence": "Grande litigante do catálogo CNJ identificado em RELATORIO"
  },
  {
    "literal": "art. 12, inciso I",
    "start": 653,
    "end": 670,
    "char_count": 17,
    "section": "RELATORIO",
    "entity_type": "NORMA",
    "normalized_value": {
      "diploma": "PENDENTE_CONTEXTO",
      "artigo": "12",
      "paragrafo": null,
      "inciso": "I",
      "alinea": null,
      "lei_ano": null,
      "raw_reference": "art. 12, inciso I"
    },
    "role": "TESE_ALEGADA",
    "confidence": 0.75,
    "evidence": "Citado no Relatório nas alegações das partes"
  },
  {
    "literal": "2%",
    "start": 760,
    "end": 762,
    "char_count": 2,
    "section": "FUNDAMENTACAO",
    "entity_type": "VALOR",
    "normalized_value": {
      "amount": 2.0,
      "currency": "PERCENT",
      "is_percentage": true,
      "raw_text": "2%",
      "qualifier": "percentual_generico"
    },
    "role": "VALOR_MENCIONADO",
    "confidence": 0.95,
    "evidence": "Percentual citado no texto"
  }
]
```
