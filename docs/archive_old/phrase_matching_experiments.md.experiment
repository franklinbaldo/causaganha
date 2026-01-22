# Experimentos: Comparação de Frases vs RAG k-NN

**Data:** 2026-01-18
**Objetivo:** Testar se frases-chave simples podem substituir RAG k-NN

---

## 🎯 Hipótese Original

> "E se compararmos a similaridade da decisão com frases-chave simples?"
> - Frase 1: "O autor venceu"
> - Frase 2: "O réu venceu"

**Vantagem esperada:** Extrema simplicidade + custo mínimo

---

## 🧪 Experimentos Realizados

### Experimento 1: 2 Frases Simples (WIN vs LOSS)

**Frases:**
- AUTOR VENCEU: "O autor da ação judicial venceu a causa e o réu foi condenado a pagar."
- RÉU VENCEU: "O réu venceu a ação judicial e o pedido do autor foi negado."

**Dataset:** 7 decisões (5 WIN, 2 LOSS)

**Resultado:**
- Acurácia: **85.7%**
- WIN: 5/5 (100%)
- LOSS: 1/2 (50%)

**Conclusão:** ✅ Funciona MUITO BEM quando só há 2 categorias!

---

### Experimento 2: 2 Frases com Dataset Completo

**Dataset:** 30 decisões (5 WIN, 2 LOSS, 1 PARTIAL, 22 UNKNOWN)

**Resultado:**
- Acurácia geral: **20.0%**
- WIN: 5/5 (100%) ✅
- LOSS: 1/2 (50%) ⚠️
- UNKNOWN: 0/22 (0%) ❌
- PARTIAL: 0/1 (0%) ❌

**Problema:** Sistema FORÇA escolha entre WIN ou LOSS. Todos os UNKNOWN foram classificados erroneamente.

**Conclusão:** ❌ Não funciona com múltiplas categorias.

---

### Experimento 3: 4 Frases (WIN/LOSS/UNKNOWN/PARTIAL)

**Frases:**
- WIN: "O autor da ação judicial venceu a causa e o réu foi condenado a pagar."
- LOSS: "O réu venceu a ação judicial e o pedido do autor foi negado e julgado improcedente."
- UNKNOWN: "Este é apenas um despacho processual ou intimação, sem julgamento definitivo do mérito da ação."
- PARTIAL: "A decisão foi parcialmente favorável ao autor e parcialmente ao réu, com procedência parcial."

**Dataset:** 30 decisões (todas as categorias)

**Resultado:**
- Acurácia geral: **36.7%**
- WIN: 2/5 (40%)
- LOSS: 1/2 (50%)
- UNKNOWN: 8/22 (36.4%)
- PARTIAL: 0/1 (0%)

**Problema:** Scores muito próximos entre as 4 frases!

**Exemplo de erro:**
```
ID 67810616: LOSS (previsto ERRADO: WIN)
  WIN:     0.619  ← Escolheu (ERRADO)
  UNKNOWN: 0.613  ← Quase empatado!
  PARTIAL: 0.593
  LOSS:    0.590  ← Real (diferença: 0.029)
```

**Conclusão:** ⚠️ Melhor que 2 frases, mas ainda muito abaixo do RAG k-NN.

---

## 📊 Comparação Final: Todos os Métodos

| Método | Acurácia | Custo/Decisão | Complexidade | Status |
|--------|----------|---------------|--------------|--------|
| **Frases Genéricas (múltiplas)** | 13.3% | $0.00001 | Baixa | ❌ Falhou |
| **2 Frases Simples** | 20.0% | $0.000003 | Muito baixa | ❌ Só funciona com 2 categorias |
| **4 Frases Simples** | 36.7% | $0.000004 | Baixa | ⚠️ Scores muito próximos |
| **RAG k-NN** | **83.3%** | $0.000008 | Média | ✅ **VENCEDOR** |
| **LLM (Gemini Flash)** | ~85% | $0.000420 | Alta | ✅ Referência |

---

## 🔬 Análise: Por Que Frases Simples Falham?

### Problema 1: Scores Muito Próximos

**Diferença média entre frases:** 0.0345
**Diferença mínima:** 0.0007 (praticamente empate!)
**Diferença máxima:** 0.0814

Com diferenças tão pequenas, o sistema "chuta" entre categorias muito similares.

### Problema 2: Falta de Contexto Jurídico

Frases genéricas como "O autor venceu" não capturam:

1. **Vocabulário jurídico específico:**
   - "julgo procedente" vs "julgo improcedente"
   - "defiro" vs "indefiro"
   - "acolho" vs "rejeito"
   - "provimento" vs "desprovimento"

2. **Estrutura de sentenças brasileiras:**
   - "Vistos, etc. Trata-se de..."
   - "Relatório dispensado..."
   - "Decido..."
   - "Dispositivo..."

3. **Variabilidade de linguagem:**
   - Diferentes juízes escrevem diferente
   - Diferentes tribunais têm estilos próprios
   - Diferentes tipos de ação têm estruturas diferentes

### Problema 3: UNKNOWN é Majoritário

No ground truth:
- UNKNOWN: 22/30 (73.3%)
- WIN: 5/30 (16.7%)
- LOSS: 2/30 (6.7%)
- PARTIAL: 1/30 (3.3%)

**Dataset desbalanceado** dificulta aprendizado por similaridade simples.

---

## ✅ Por Que RAG k-NN Funciona Melhor?

### Vantagem 1: Usa Decisões REAIS

Em vez de frases genéricas, compara com decisões COMPLETAS:

```python
# Frase genérica (não funciona):
"O autor venceu a ação judicial"

# Decisão real (funciona):
"""
PODER JUDICIÁRIO DO ESTADO DE RONDÔNIA
Tribunal de Justiça de Rondônia
Espigão do Oeste - 1ª Vara Genérica

Processo n.: 7001187-42.2022.8.22.0008
Classe: Procedimento Comum Cível
Assunto: Aposentadoria por Invalidez

SENTENÇA

Vistos, etc.

Trata-se de ação de concessão de aposentadoria...

DECIDO.

Julgo PROCEDENTE o pedido do autor para condenar
o INSS a implantar o benefício...

Condeno o réu ao pagamento de honorários...
"""
```

### Vantagem 2: Captura Contexto Local

Decisões similares têm:
- Mesmo tribunal (Espigão do Oeste)
- Mesmo tipo de ação (Previdenciário)
- Mesmo réu (INSS)
- Estrutura textual similar

### Vantagem 3: Votação por Maioria

Com k=5:
- Se 4 de 5 vizinhos são WIN → Alta confiança
- Se 3 de 5 são WIN, 2 UNKNOWN → Média confiança
- Se 2 WIN, 2 LOSS, 1 UNKNOWN → Baixa confiança (usar LLM)

### Vantagem 4: Explicabilidade

Podemos ver QUAIS decisões influenciaram:

```
Decisão nova classificada como WIN porque:
  Vizinho 1: ID 67811602 (WIN, sim: 0.95)
  Vizinho 2: ID 67811603 (WIN, sim: 0.93)
  Vizinho 3: ID 67811605 (WIN, sim: 0.91)
  Vizinho 4: ID 67809720 (UNKNOWN, sim: 0.87)
  Vizinho 5: ID 67810616 (WIN, sim: 0.85)

Votos: WIN=4, UNKNOWN=1 → Classificação: WIN (80% confiança)
```

---

## 💡 Insights e Aprendizados

### 1. Simplicidade tem Limites

**2 frases funcionam bem APENAS para classificação binária simples.**

Mas análise jurídica requer nuance:
- Sentenças vs Despachos (WIN/LOSS vs UNKNOWN)
- Procedência total vs parcial (WIN vs PARTIAL)
- Diferentes graus de confiança

### 2. Contexto é Fundamental

Embeddings de **frases isoladas** não capturam a **riqueza do texto jurídico**.

RAG usa **decisões completas** como referência = muito mais contexto.

### 3. Desbalanceamento Importa

Com 73% de UNKNOWN no dataset:
- Frases genéricas tendem a classificar tudo como UNKNOWN
- Ou forçam WIN/LOSS ignorando UNKNOWN
- RAG equilibra melhor com votação k-NN

### 4. Trade-off Custo vs Acurácia

```
Custo crescente →
2 Frases: $0.000003, 20% acurácia
4 Frases: $0.000004, 37% acurácia
RAG k-NN: $0.000008, 83% acurácia  ← Sweet spot!
LLM:      $0.000420, 85% acurácia
```

**RAG oferece melhor custo-benefício:** 83% de acurácia a $0.000008 (52x mais barato que LLM, apenas 2x mais caro que 4 frases).

---

## 🎯 Recomendação Final

### Para CausaGanha: Use RAG k-NN

**Justificativa:**

| Critério | Avaliação |
|----------|-----------|
| **Acurácia** | ✅ 83.3% (quase igual a LLM) |
| **Custo** | ✅ $0.000008 (98% economia vs LLM) |
| **Simplicidade** | ✅ Requer apenas ground truth |
| **Escalabilidade** | ✅ Processa milhões de decisões |
| **Explicabilidade** | ✅ Mostra decisões similares |
| **Manutenção** | ✅ Só precisa expandir ground truth |

### Quando Usar Cada Método

| Cenário | Método Recomendado |
|---------|-------------------|
| **Classificação binária simples** | 2 Frases (WIN vs LOSS) |
| **Análise completa (4 categorias)** | RAG k-NN |
| **Máxima precisão (custo não importa)** | LLM |
| **Híbrido: RAG + LLM fallback** | RAG (confiança ≥70%) + LLM (confiança <70%) |

---

## 📈 Próximos Passos

### 1. Expandir Ground Truth

**Meta:** 100-500 decisões validadas balanceadas

Distribuição ideal:
- WIN: 150 decisões
- LOSS: 150 decisões
- UNKNOWN: 100 decisões
- PARTIAL: 100 decisões

**Resultado esperado:** Acurácia 83% → 85-90%

### 2. Implementar Híbrido RAG + LLM

```python
def classify_hybrid(texto: str) -> dict:
    # 1. Tentar RAG primeiro
    rag_result = classify_with_knn(texto, k=5)

    # 2. Se confiança alta, usar RAG
    if rag_result["confidence"] >= 0.70:
        return rag_result  # $0.000008

    # 3. Se confiança baixa, usar LLM
    else:
        return analyze_with_llm(texto)  # $0.000420
```

**Economia estimada:** 60-70% dos casos com alta confiança RAG = 60-70% de economia total.

### 3. Testar com Batch API

Usar Google Batch API para embeddings:
- Custo: 50% menor ($0.000004 vs $0.000008)
- Processamento assíncrono
- Ideal para lotes grandes

---

## ✅ Conclusão

**A ideia original de comparação com frases simples era boa, mas tem limitações fundamentais.**

**Veredicto:**
- ✅ **2 frases:** Funciona para classificação binária simples (WIN vs LOSS)
- ⚠️ **4 frases:** Melhora mas scores muito próximos (36.7%)
- ✅ **RAG k-NN:** Melhor custo-benefício geral (83.3% a $0.000008)
- ✅ **LLM:** Máxima precisão mas caro (~85% a $0.000420)

**Recomendação:** Usar **RAG k-NN** como método principal, com **LLM fallback** para casos de baixa confiança.

---

**Créditos:** Experimento sugerido pelo usuário e implementado com validação completa.
