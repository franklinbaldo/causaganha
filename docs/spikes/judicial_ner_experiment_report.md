# Relatório de Experimentos: Judicial Multi-Algorithm NER (Grounded em Dados DJEN Reais)

Este relatório documenta a avaliação empírica do pipeline de NER especializado sobre **três corpora reais do DJEN**:
1. **Benchmark de Ouro** (`data/benchmark/decisions/*.md`): 100 decisões judiciais completas com frontmatter YAML e anotações ricas.
2. **Amostra Multitribunal Nacional** (`data/segmenter_samples/*.jsonl`): 849 intimações reais de 66 arquivos cobrindo tribunais de todos os estados (TJSP, TJRJ, TJBA, TJRO, TRF2, TRF3, TRF5, etc.).
3. **Tabela Consolidada de Ouro** (`data/benchmark/gold_benchmark.parquet`): 300 decisões com classes processuais e valores.

## 1. Desempenho e Throughput em CPU (Intel/AMD x86_64, 1 Core)

| Algoritmo Especializado | Mecanismo | Throughput (doc/s) | Média (ms) | p95 (ms) | Entidades |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. CNJ** | Regex + Módulo 97 | 6189.9 | 0.16 | 0.43 | 231 |
| **2. Normas** | Parser Léxico + Anáfora | 1462.4 | 0.68 | 1.90 | 821 |
| **3. Valores** | Regex Moeda/% + Janela Seccional | 3201.0 | 0.31 | 0.88 | 229 |
| **4. Datas** | Prazos CPC + ISO-8601 | 1944.5 | 0.51 | 1.39 | 543 |
| **5. Organizações** | Trie/Aho-Corasick Top 100 CNJ | 352.4 | 2.84 | 7.86 | 388 |
| **6. Pessoas, Advogados e OAB** | Grounding DJEN + Contexto | 1027.9 | 0.97 | 2.48 | 480 |
| **7. PIPELINE COMPOSTO SECCIONAL** | Orquestrador + Grafo | **130.6** | **7.66** | **20.40** | **2384** |

## 2. Aferição de Qualidade e Concordância com Metadados Oficiais

- **Validação CNJ Módulo 97 (Res. CNJ nº 65/2008)**: **230/231 (99.6%)** de dígitos verificadores matematicamente íntegros no texto das decisões.
- **Recall de Fundamentos Legais (`legal_bases`)**: **218/218 (100.0%)** das normas fundamentadoras identificadas.
- **Grounding de Magistrados e Relatores (`judge_name`)**: **50/50 (100.0%)** dos magistrados constantes no metadado ouro foram localizados no texto e devidamente classificados no papel `MAGISTRADO`.
- **Inscrições na OAB e Advogados**: Identificadas 480 menções de patronos e inscrições na OAB com extração precisa de estado, número e tipo.
- **Corpus Multitribunal (849 intimações reais)**: Processado a **223.0 docs/s**, extraindo um total de **13,676 entidades** (16.1 por documento).

## 3. Distribuição de Entidades no Corpus Multitribunal (849 Decisões Reais)

| Tipo de Entidade | Total Extraído | Média por Documento | Papéis Principais Identificados |
| :--- | :--- | :--- | :--- |
| `NORMA` | 5,277 | 6.2 | Normas de mérito/admissibilidade, processos citados, condenações |
| `DATA` | 2,935 | 3.5 | Normas de mérito/admissibilidade, processos citados, condenações |
| `CNJ` | 1,678 | 2.0 | Normas de mérito/admissibilidade, processos citados, condenações |
| `ORGANIZACAO` | 1,549 | 1.8 | Normas de mérito/admissibilidade, processos citados, condenações |
| `VALOR` | 1,471 | 1.7 | Normas de mérito/admissibilidade, processos citados, condenações |
| `OAB` | 686 | 0.8 | Normas de mérito/admissibilidade, processos citados, condenações |
| `PESSOA` | 80 | 0.1 | Normas de mérito/admissibilidade, processos citados, condenações |

## 4. Exemplo de Decisão Real Anotada no Grafo Seccional

```json
{
  "arquivo": "TJRO-2026-05-27-1051730411150002516.md",
  "metadados_oficiais_djen": {
    "assunto_principal": "Aposentadoria Rural",
    "classe_processual": "Procedimento Comum Cível",
    "confidence_score": 1.0,
    "court": "TJRO",
    "decision_reasoning": "A autora comprovou o preenchimento dos requisitos para a concessão do benefício de aposentadoria por idade rural.",
    "decision_type": "sentença",
    "fase_processual": "conhecimento",
    "intimation_id": 1051730411150002516,
    "is_human_verified": false,
    "judge_name": "Ana Lucia Mortari",
    "keywords": [
      "aposentadoria por idade rural",
      "INSS",
      "honorários advocatícios",
      "duplo grau de jurisdição"
    ],
    "legal_bases": [
      "art. 5º, I, da Lei Estadual nº 3.896/16",
      "artigo 85, §3º, I, do CPC",
      "Súmula 111 do STJ",
      "art. 496, I, do CPC",
      "Súmula 490 do STJ"
    ],
    "llm_model": "gemini/gemini-2.5-flash-lite",
    "outcome": "procedente",
    "plaintiff_won": true,
    "precedents": {},
    "proposed_regex": null,
    "schema_version": "1.2.0",
    "summary": "O juiz julgou procedente o pedido de concessão de aposentadoria por idade rural, condenando o INSS ao pagamento de honorários advocatícios.",
    "text_uuid": "9c08cba0f1f84e56b5edd0910cd54c3e",
    "validated_at": "2026-05-27T23:50:03.677902",
    "valor_causa": null,
    "valor_condenacao": null
  },
  "secoes_detectadas": [
    "cabecalho",
    "relatorio",
    "fundamentacao",
    "dispositivo"
  ],
  "amostra_entidades": [
    {
      "literal": "ESTADO DE RONDÔNIA",
      "start": 20,
      "end": 38,
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
      "literal": "7000685-89.2025.8.22.0011",
      "start": 235,
      "end": 260,
      "char_count": 25,
      "section": "CABECALHO",
      "entity_type": "CNJ",
      "normalized_value": {
        "numero_formatado": "7000685-89.2025.8.22.0011",
        "sequencial": "7000685",
        "digito_verificador": "89",
        "ano": 2025,
        "ramo_justica": 8,
        "tribunal": 22,
        "origem": "0011",
        "is_valid_mod97": true
      },
      "role": "PROCESSO_PRINCIPAL",
      "confidence": 1.0,
      "evidence": "Inferido provisoriamente do cabeçalho por ausência de metadados do DJEN"
    },
    {
      "literal": "CELIO DA CRUZ",
      "start": 466,
      "end": 489,
      "char_count": 13,
      "section": "CABECALHO",
      "entity_type": "PESSOA",
      "normalized_value": {
        "nome": "CELIO DA CRUZ",
        "cpf_cnpj": null,
        "polo": "ADVOGADO"
      },
      "role": "ADVOGADO",
      "confidence": 0.9,
      "evidence": "Advogado associado à OAB identificada no texto"
    },
    {
      "literal": "CELIO DA CRUZ",
      "start": 474,
      "end": 487,
      "char_count": 13,
      "section": "CABECALHO",
      "entity_type": "PESSOA",
      "normalized_value": {
        "nome": "CELIO DA CRUZ",
        "cpf_cnpj": null,
        "polo": "ADVOGADO"
      },
      "role": "ADVOGADO",
      "confidence": 0.85,
      "evidence": "Advogado extraído do rótulo de cabeçalho na ausência de metadado DJEN"
    },
    {
      "literal": "OAB nº RO5443A",
      "start": 489,
      "end": 503,
      "char_count": 14,
      "section": "CABECALHO",
      "entity_type": "OAB",
      "normalized_value": {
        "uf": "RO",
        "numero": "5443",
        "tipo_inscricao": "A",
        "nome_advogado": "CELIO DA CRUZ"
      },
      "role": "ADVOGADO",
      "confidence": 0.95,
      "evidence": "Inscrição na OAB identificada no texto"
    },
    {
      "literal": "INSS",
      "start": 509,
      "end": 513,
      "char_count": 4,
      "section": "CABECALHO",
      "entity_type": "ORGANIZACAO",
      "normalized_value": {
        "canonical_name": "INSS_INSTITUTO_NACIONAL_SEGURO_SOCIAL",
        "catalog_role": "ORGAO_PUBLICO"
      },
      "role": "ORGAO_PUBLICO",
      "confidence": 0.99,
      "evidence": "Grande litigante do catálogo CNJ identificado em CABECALHO"
    }
  ]
}
```
