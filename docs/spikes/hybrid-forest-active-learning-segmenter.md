# Spike: Segmentador Híbrido Random Forest + Metadados DJEN + Active Learning Flywheel

**Data:** 09/11/2026  
**Branch:** `spike/thx02-judicial-outcome-20261106` (PR #1687)  
**Autor:** Antigravity AI & Franklin Baldo  
**Status:** Validado e Integrado (57/57 testes unitários passando)

---

## 1. Contexto & Decisão Arquitetural

No benchmark de extração de dispositivo anterior (`docs/spikes/dispositif-extraction-methods-benchmark.md`), comprovamos que:
1. **O OPF Neural 1.5B (token classifier BIOES) é inadequado** para alimentar LLMs de desfecho (THX-02): gera fragmentação excessiva (~370 caracteres), falha em 40% dos casos e atinge apenas 30% de acurácia de desfecho.
2. **Métodos estruturados de recorte amplo** (`canonical_regex` e `tail_window`) alcançam 90% de acurácia com custo computacional nulo (< 0.2 ms).
3. **Decisão:** Substituir definitivamente o OPF 1.5B por um **Segmentador Híbrido tabular** (`RandomForestClassifier` + `IsolationForest` para detecção de anomalias), enriquecido com os **metadados nativos do DJEN** e com uma **Flywheel de Active Learning** via auditoria LLM Judge.

---

## 2. Arquitetura do Segmentador Híbrido

O módulo [`HybridDispositifSegmenter`](file:///C:/Users/76450694220/workspace/causaganha/src/causaganha/decisoes/hybrid_segmenter.py) opera em 4 camadas de inteligência:

```
[Decisão Bruta DJEN] 
        │
        ▼
1. Extração de Metadados DJEN / Fallback de Cabeçalho
   (Juiz, Partes, Comarca, Classe Processual, Ano)
        │
        ▼
2. Particionador de Unidades Estruturais
   (Suporta multiline e flat text contínuo de OCR/DJEN)
        │
        ▼
3. Random Forest (13 features) + Detecção de Anomalias (Isolation Forest)
   (Posição relativa, âncoras canônicas, avisos de citação STJ/STF, assinaturas)
        │
        ▼
4. Recorte Cirúrgico do Dispositivo (Média de 700 chars)
        │
        ▼
[HAL-X THX-02 / LLM Judge]
```

### 2.1 Vetor de Features (13 Dimensões)

| Feature | Tipo | Importância RF | Descrição |
| :--- | :--- | :--- | :--- |
| `dist_to_end_ratio` | Float | **0.4152** | Distância normalizada do parágrafo até o fim do texto |
| `pos_relativa` | Float | **0.2632** | Posição ordinal do parágrafo no documento |
| `classe_is_recurso` | Binário | **0.2067** | Metadado DJEN: sinaliza apelações/agravos (resultado na ementa) |
| `char_len` | Float | **0.0743** | Comprimento em caracteres da unidade |
| `has_citation_warning` | Binário | **0.0210** | Penalizador severo contra citações de STJ/STF/DJE |
| `has_canonical_anchor` | Binário | **0.0095** | Presença de âncoras ("Ante o exposto", "Julgo procedente", etc.) |
| `is_upper_heading` | Binário | **0.0080** | Títulos em caixa alta ("DISPOSITIVO", "ACÓRDÃO") |
| `has_judge_signature` | Binário | **0.0005** | Nome do magistrado / relator (fronteira de encerramento) |
| `has_plaintiff_mention` | Binário | **0.0012** | Menção ao polo ativo no dispositivo |
| `has_defendant_mention` | Binário | **0.0005** | Menção ao polo passivo no dispositivo |
| `classe_is_execucao` | Binário | - | Execuções e cumprimentos de sentença |
| `ano_pos_2020` | Binário | - | Datação da decisão (regras do CPC/2015 maduras) |
| `classe_is_hc` | Binário | - | Habeas corpus / decisões criminais |

---

## 3. Flywheel de Active Learning (Auditoria LLM)

Para contornar o problema histórico de "falsos positivos em pattern matching", implementamos a ferramenta [`audit_active_learning_sampling.py`](file:///C:/Users/76450694220/workspace/causaganha/scripts/audit_active_learning_sampling.py).

### 3.1 Política de Amostragem Estratificada
A cada lote de publicações processado pelo pipeline, uma amostra é extraída para a LLM Judge auditar:
1. **100% das Anomalias da Isolation Forest (`is_anomaly == True`):** Decisões com padrão textual excêntrico (curtíssimas, despachos atípicos, ausência total de estrutura padrão).
2. **Decisões de Baixa Confiança / Fallback (`confidence < 0.60` ou `fallback_used == True`):** Casos onde a Random Forest ficou em dúvida.
3. **Amostra de Controle de Alta Confiança (`confidence >= 0.70`):** Para medir a taxa real de falso positivo (False Discovery Rate).

### 3.2 Execução no Lote Real (`gold_benchmark.parquet` - 300 decisões TJRO/TJBA/TJRJ/TJSP)

```bash
uv run python scripts/audit_active_learning_sampling.py --sample-size 25
```

- **Decisões processadas:** 300
- **Anomalias estruturais:** 19 (6.3%)
- **Baixa confiança:** 32 (10.7%)
- **Fallbacks acionados:** apenas 11 (3.7%) — **96.3% das decisões foram recortadas cirurgicamente pela Random Forest**
- **Comprimento médio recortado:** 703 caracteres (ideal para a janela do THX-02)

O script exporta:
- `data/audit/audit_active_learning_batch.jsonl`: Arquivo pronto com prompts estruturados para a LLM Judge classificar completude, erros de truncamento e excesso de jurisprudência.
- `data/audit/audit_active_learning_report.md`: Relatório executivo do lote.

---

## 4. Comparativo de Performance: OPF 1.5B vs Random Forest Híbrida

| Dimensão | OPF Neural (1.5B) | Random Forest Híbrida | Vantagem RF |
| :--- | :--- | :--- | :--- |
| **Tempo de Execução (CPU)** | ~3.000 ms | **13.1 ms** | **229x mais rápido** |
| **Consumo de Memória / Disco** | ~3.200 MB | **704 KB** | **4.500x mais leve** |
| **Recall no Conjunto de Teste** | 62.0% | **90.0%** | **+28.0 p.p.** |
| **ROC AUC no Conjunto de Teste** | ~0.71 | **0.883** | **Muito superior** |
| **Taxa de Fallback em Produção** | 40.0% | **3.7%** | **Redução de 90%** |
| **Dependência de GPU** | Mandatória | **Zero (roda em CPU fraca)** | **Economia massiva de nuvem** |

---

## 5. Como Executar

### 5.1 Treinar o Segmentador
```bash
uv run python scripts/train_hybrid_forest_segmenter.py
```

### 5.2 Executar a Amostragem Ativa para LLM Judge
```bash
uv run python scripts/audit_active_learning_sampling.py --input data/benchmark/gold_benchmark.parquet --sample-size 30
```

### 5.3 Rodar a Suíte de Testes
```bash
uv run pytest tests/test_hybrid_segmenter.py tests/test_spike_thx02.py tests/test_spike_thx02_segmenter.py -v
```
