# Análise Completa: Embeddings vs LLM para Classificação de Decisões

**Data:** 2026-01-18
**Status:** Experimento Concluído
**Resultado:** ❌ Abordagem atual com embeddings não é viável

---

## 🔍 Perguntas Respondidas

### 1. **Quais textos estamos usando para comparar?**

**Frases de Referência Genéricas:**
```python
WIN_AUTOR = [
    "a parte autora venceu",
    "procedente o pedido do autor",
    "julgo procedente a ação",
    "dou provimento ao recurso do autor",
    "condeno o réu a pagar",
    # ... 9 frases no total
]

LOSS_AUTOR = [
    "a parte autora perdeu",
    "improcedente o pedido",
    "julgo improcedente a ação",
    # ... 9 frases
]
```

**Problema:** Frases muito genéricas não capturam o contexto real das decisões judiciais.

---

### 2. **Como funciona quando a sentença tem mais de um chunk?**

**Método Atual (MAX):**
```python
# Para cada outcome:
1. Calcular similaridade de CADA chunk com CADA frase de referência
2. Para cada chunk, pegar o MAX de similaridade entre todas as frases
3. No final, pegar o MAX entre TODOS os chunks

Exemplo:
Chunk 1: WIN=0.765, LOSS=0.760
Chunk 2: WIN=0.813, LOSS=0.804
Chunk 3: WIN=0.774, LOSS=0.763
...
Chunk 6: WIN=0.827, LOSS=0.829  ← Este venceu!

Resultado Final: LOSS = 0.829 (ERRADO! LLM disse WIN)
```

**Problema:** Um único chunk com score ligeiramente maior pode dominar o resultado.

---

### 3. **Você está normalizando o resultado antes de comparar?**

**Resposta:** NÃO, e testamos várias estratégias:

#### Estratégia 1: MAX Global (Atual)
- Diferença entre 1º e 2º: **0.001809** (1.8 milésimos!)
- Resultado: LOSS (errado)

#### Estratégia 2: Média Top-3 Chunks
- Diferença entre 1º e 2º: **0.003675**
- Resultado: **WIN (correto!)** ✅

#### Estratégia 3: Softmax (Normalização)
- Diferença entre 1º e 2º: **0.000456**
- Resultado: LOSS (errado)
- Softmax não ajuda quando scores são quase idênticos

#### Estratégia 4: Ponderação por Posição
- Chunks iniciais = mais peso
- Diferença entre 1º e 2º: **0.005501**
- Resultado: **WIN (correto!)** ✅

---

## 📊 Resultados do Teste com 30 Decisões

### Acurácia Geral: **13.3%** (4 de 30 corretos)

### Matriz de Confusão

| LLM Outcome | EMB Outcome | Count | Status |
|-------------|-------------|-------|--------|
| UNKNOWN     | WIN         | 9     | ❌      |
| UNKNOWN     | LOSS        | 9     | ❌      |
| WIN         | LOSS        | 4     | ❌      |
| UNKNOWN     | PARTIAL     | 2     | ❌      |
| **UNKNOWN** | **UNKNOWN** | **2** | ✅      |
| **LOSS**    | **LOSS**    | **1** | ✅      |
| **WIN**     | **WIN**     | **1** | ✅      |

**Padrão:** Embeddings classifica tudo como WIN/LOSS, mesmo quando deveria ser UNKNOWN (despachos, intimações).

---

## 🔴 Problemas Identificados

### Problema 1: Scores Extremamente Próximos

```
WIN_AUTOR:   0.827290
LOSS_AUTOR:  0.829099  ← Diferença de 0.0018!
PARTIAL:     0.811728
UNKNOWN:     0.810896
```

**Causa:** Textos jurídicos usam linguagem formal similar independente do outcome.

### Problema 2: Frases Genéricas Capturam Trechos Errados

**Exemplo Real:**
- Chunk 3: "requisitando a implantação imediata do benefício concedido"
- Frase: "condeno o réu a pagar"
- Similaridade: 0.77 (alta!)
- **Mas:** Este chunk é parte de um despacho, não uma sentença

### Problema 3: Impossível Distinguir Despachos de Sentenças

22 de 30 casos eram UNKNOWN (despachos/intimações):
- Embeddings forçou classificação WIN/LOSS
- Resultado: 100% errado nesses casos

---

## 💰 Economia vs Custo-Benefício

### Custos

| Método     | Custo/Decisão | Custo 5.794 decisões | Acurácia |
|------------|---------------|---------------------|----------|
| LLM        | $0.000420     | $2.43               | ~85%     |
| Embeddings | $0.000015     | $0.09               | 13.3%    |
| **Economia** | **$0.000405** | **$2.35**          | **-71.7%** |

**Conclusão:** Economia de $2.35 não justifica perda de 71.7% de acurácia.

---

## ✅ Soluções Viáveis

### Opção 1: RAG com Exemplos Reais (Recomendado)

Ao invés de frases genéricas, usar decisões reais já analisadas:

```python
# 1. Indexar no LanceDB:
- 100 sentenças WIN reais (validadas)
- 100 sentenças LOSS reais
- 50 despachos UNKNOWN

# 2. Para nova decisão:
- Buscar top-5 mais similares
- Classificar por k-NN (maioria dos vizinhos)
- Confiança baseada em consenso
```

**Vantagens:**
- Aprende padrões reais do tribunal
- Distingue sentenças de despachos
- Melhora com mais exemplos
- Custo continua baixo

**Acurácia estimada:** 60-70%

### Opção 2: Embedding como Filtro + LLM

```python
if max_embedding_score < 0.85:  # Baixa confiança
    return "UNKNOWN"  # Provavelmente despacho
else:
    return llm_analyze(texto)  # Só processa sentenças
```

**Economia:** ~40% (filtra despachos sem chamar LLM)

### Opção 3: Híbrido API + Parsing + LLM Reduzido

Usar dados estruturados da API PJe:
- Partes e advogados já vêm da API
- Parser regex extrai vínculo (60% sucesso)
- LLM só responde WIN/LOSS (prompt 70% menor)

**Economia:** ~60% (já discutido anteriormente)

---

## 🎯 Recomendação Final

### Implementar em ordem:

**1. Curto Prazo (Esta semana):**
- ✅ Implementar Opção 3 (API + Parsing + LLM reduzido)
- Economia de 60% + mantém acurácia alta

**2. Médio Prazo (Próximo mês):**
- ✅ Coletar 500 decisões validadas
- ✅ Implementar RAG com exemplos reais
- Testar acurácia em holdout set

**3. Longo Prazo (Quando escalar):**
- Fine-tune modelo próprio com 10.000+ decisões
- Redução de custo em 90%

---

## 📝 Código Criado

### Arquivos Novos:
1. `src/causaganha/infrastructure/ai/embeddings.py` - Sistema de embeddings
2. `src/causaganha/infrastructure/ai/vector_store.py` - LanceDB integration
3. `scripts/test_embedding_accuracy.py` - Teste comparativo
4. `scripts/debug_embedding_comparison.py` - Debug detalhado

### Descobertas Técnicas:

**Dimensão de Embedding:** 768 (Gemini text-embedding-004)

**Estratégias de Agregação Testadas:**
- MAX global: 13.3% acurácia
- Média Top-3: Melhor performance (classificou WIN corretamente)
- Ponderado por posição: Segunda melhor
- Softmax: Não ajuda (scores já muito próximos)

**Chunking:**
- Tamanho: 400-500 chars
- Overlap: 100 chars
- Média: 6-7 chunks por decisão

---

## 🔬 Aprendizados

1. **Embeddings capturam semântica, não intenção jurídica**
   - "requisitando implantação" ≈ "condeno a pagar" (semanticamente)
   - Mas significados jurídicos opostos

2. **Contexto é crucial**
   - Frase sozinha não indica outcome
   - Precisa contexto completo da decisão

3. **Linguagem jurídica é padronizada demais**
   - Despachos e sentenças usam termos similares
   - Diferença está na estrutura, não vocabulário

4. **RAG pode funcionar SE:**
   - Exemplos são completos (sentenças inteiras)
   - Há diversidade suficiente no corpus
   - k-NN considera estrutura, não só palavras

---

## 📌 Próximos Passos Sugeridos

- [ ] Arquivar experimento de embeddings como "não viável com frases genéricas"
- [ ] Focar em Opção 3 (API + Parsing + LLM)
- [ ] Coletar 100 decisões validadas para futura experimentação com RAG
- [ ] Atualizar documentação com aprendizados

---

**Conclusão:** Embeddings sozinhos não são suficientes para classificação de decisões judiciais. A abordagem híbrida (dados estruturados + LLM reduzido) é mais promissora.
