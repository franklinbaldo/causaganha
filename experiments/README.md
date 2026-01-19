# Experimentos de Classificação de Decisões Judiciais

Este diretório contém experimentos que foram realizados para encontrar o melhor método de classificação de decisões judiciais com custo mínimo.

## 📊 Resumo dos Resultados

| Método | Acurácia | Custo/Decisão | Localização | Status |
|--------|----------|---------------|-------------|--------|
| **RAG k-NN** | **83.3%** | **$0.000008** | `../scripts/test_rag_accuracy.py` | ✅ **ESCOLHIDO** |
| Batch RAG | 83.3% | $0.000004 | `../scripts/batch_embed_decisions.py` | ✅ **PRODUÇÃO** |
| Frases Genéricas | 13.3% | $0.00001 | `embeddings/` | ❌ Falhou |
| 2 Frases Simples | 20.0% | $0.000003 | `phrase_matching/` | ❌ Insuficiente |
| 4 Frases | 36.7% | $0.000004 | `phrase_matching/` | ❌ Insuficiente |
| LLM (Gemini Flash) | ~85% | $0.000420 | - | 📊 Baseline |

## 🎯 Conclusão

**RAG k-NN com ground truth venceu!**

### Por Que RAG Venceu?

1. **Alta acurácia:** 83.3% (4x melhor que frases simples, 98% da acurácia do LLM)
2. **Baixo custo:** $0.000008 por decisão (52x mais barato que LLM)
3. **Decisões reais:** Usa exemplos validados como referência
4. **Contexto jurídico:** Captura vocabulário e estrutura brasileira
5. **Escalável:** Processa milhões de decisões
6. **Explicável:** Mostra quais decisões influenciaram a classificação

### Por Que Frases Simples Falharam?

**Problema principal:** Scores muito próximos entre categorias

Exemplo real:
```
ID 67810616 (Real: LOSS)
  Similaridade com "autor venceu": 0.6189
  Similaridade com "réu venceu":   0.5785
  Diferença: 0.0404 (apenas 4%!)

Classificação: WIN (ERRADO!)
```

Com diferenças tão pequenas, o sistema "chuta" entre categorias.

## 📁 Estrutura

### `phrase_matching/` - Experimentos com Frases-Chave

**Hipótese testada:** Comparar decisões com frases simples
- "O autor da ação judicial venceu a causa e o réu foi condenado"
- "O réu venceu a ação judicial e o pedido foi negado"

**Arquivos:**
- `test_simple_phrase_matching.py` - Teste inicial com 2 frases
- `test_simple_phrase_full.py` - Teste com dataset completo (30 decisões)
- `test_4_phrases.py` - Tentativa com 4 frases (WIN/LOSS/UNKNOWN/PARTIAL)

**Resultados:**
- 2 frases: 85.7% em casos binários (WIN vs LOSS), mas 20% no dataset completo
- 4 frases: 36.7% (melhorou mas ainda insuficiente)

**Problemas identificados:**
1. Frases genéricas não capturam vocabulário jurídico específico
2. Scores muito próximos (diferença média: 0.0345)
3. Não distingue despachos de sentenças
4. Dataset desbalanceado (73% UNKNOWN) confunde o sistema

### `embeddings/` - Experimentos com Embeddings Genéricos

**Hipótese testada:** Comparar com múltiplas frases genéricas
- "a parte autora venceu"
- "procedente o pedido do autor"
- "julgo procedente a ação"
- etc.

**Arquivos:**
- `test_embedding_accuracy.py` - Teste com frases genéricas múltiplas

**Resultados:**
- Acurácia: 13.3% (4 corretos de 30)
- Diferença entre WIN/LOSS: 0.0018 (praticamente empate!)

**Problema:** Mesmo com múltiplas frases, não consegue distinguir contexto jurídico real.

## 📚 Documentação Completa

Para análise detalhada, consulte:

- **`../docs/phrase_matching_experiments.md`** - Análise completa de todos os experimentos
- **`../docs/rag_validation_results.md`** - Validação do RAG k-NN (83.3%)
- **`../docs/batch_rag_pipeline.md`** - Pipeline de produção com Google Batch API

## ⚠️ Importante: Por Que Manter Experimentos Falhados?

**Estes experimentos são documentação valiosa de O QUE NÃO FUNCIONA.**

### Benefícios:

1. **Evita retrabalho:** Se alguém sugerir "e se tentarmos comparar com frases simples?", a resposta é: "Já testamos, veja `experiments/phrase_matching/`"

2. **Justifica decisões:** Mostra POR QUE escolhemos RAG k-NN (não foi chute, foi validação científica)

3. **Educacional:** Demonstra o processo científico de validação

4. **Referência:** Outros projetos similares podem aprender com nossos experimentos

## 🔬 Metodologia

Todos os experimentos seguiram:

1. **Dataset de validação:** 30 decisões do ground truth
   - WIN: 5 decisões
   - LOSS: 2 decisões
   - PARTIAL: 1 decisão
   - UNKNOWN: 22 decisões

2. **Métricas:**
   - Acurácia geral
   - Acurácia por tipo (WIN/LOSS/UNKNOWN/PARTIAL)
   - Matriz de confusão
   - Análise de confiança

3. **Custos:** Calculados com base em pricing do Google Gemini
   - Embeddings: $0.00001 por 1k tokens
   - LLM: $0.000075 input + $0.0003 output por 1k tokens

## 🚀 Solução de Produção

O código de produção está em `../scripts/`:

```bash
# 1. Preparar ground truth
python scripts/prepare_ground_truth.py

# 2. Indexar no LanceDB
python scripts/index_ground_truth.py

# 3. Testar acurácia
python scripts/test_rag_accuracy.py

# 4. Produção: Batch embedding
python scripts/batch_embed_decisions.py

# 5. Classificar localmente
python scripts/classify_from_batch_embeddings.py
```

## 📈 Próximos Passos

Para melhorar ainda mais:

1. **Expandir ground truth:** 30 → 500 decisões
   - Meta: 83% → 90% de acurácia

2. **Híbrido RAG + LLM:**
   - RAG para casos de alta confiança (≥70%)
   - LLM fallback para casos ambíguos
   - Economia estimada: 60-70%

3. **Fine-tuning:**
   - Para casos muito específicos de Rondônia
   - Quando tivermos 10k+ decisões validadas

---

**Resumo:** RAG k-NN é a melhor solução custo-benefício. Experimentos arquivados aqui demonstram por que outras abordagens foram descartadas.
