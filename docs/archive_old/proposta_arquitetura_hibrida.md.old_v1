# Arquitetura Híbrida API+LLM - CausaGanha

## 🎯 Objetivo

Reduzir custos em 60-80% usando dados estruturados da API PJe + parsing de texto simples, deixando LLM apenas para casos complexos.

## 📊 Descobertas da Análise

### Dados Disponíveis na API

1. **Partes** (`destinatarios`): ✅ 100% confiável
   - Nome da parte
   - Polo (A=Ativo, P=Passivo, T=Terceiro, D=Outros)

2. **Advogados** (`destinatarioadvogados`): ✅ 100% confiável
   - Nome completo
   - Número OAB
   - UF OAB

3. **Vínculo advogado→parte**: ❌ NÃO existe na API
   - Precisa ser extraído do texto
   - 60% dos casos têm padrão regex parseável
   - 40% precisam LLM

## 🏗️ Arquitetura em Camadas

### Camada 1: Dados Estruturados (0 custo)
```python
# Já vem da API de graça
partes = [
    {"nome": "JOÃO", "polo": "A"},
    {"nome": "INSS", "polo": "P"}
]
advogados = [
    {"nome": "MARIA", "oab": "RO1234"},
    {"nome": "PROCURADORIA FEDERAL", "oab": None}
]
```

### Camada 2: Parsing Regex (0 custo, 60% sucesso)
```python
# Pattern matching no texto
PADRÃO ENCONTRADO EM 60% DOS CASOS:
"Advogado do(a) REQUERENTE: MARIA - RO1234"
"Advogado do(a) REQUERIDO: PROCURADORIA FEDERAL"

→ Vincula automaticamente: MARIA representa JOÃO (Ativo)
→ Vincula automaticamente: PROCURADORIA representa INSS (Passivo)
```

### Camada 3: LLM Reduzido (60% economia)
```python
# Para casos com matching bem-sucedido:
prompt = f"""
Partes já identificadas:
- Ativo: {parte_ativa} (representado por {adv_ativo})
- Passivo: {parte_passiva} (representado por {adv_passivo})

APENAS RESPONDA:
- Outcome: WIN/LOSS/PARTIAL/UNKNOWN
- Resumo em 1 frase
"""

# Para casos sem matching (40%):
prompt = """
<prompt completo atual>
"""
```

## 💰 Economia Estimada

| Cenário | Tokens Médios | Custo (5.794 decisões) |
|---------|--------------|------------------------|
| Atual (LLM completo) | 2000 | ~$50 |
| Híbrido (60% reduzido) | 800 | ~$20 |
| **Economia** | **-60%** | **$30** |

## 📋 Plano de Implementação

### Sprint 1: Coleta de Dados Estruturados (2-3h)
- [ ] Modificar `collect.py` para salvar `destinatarios`
- [ ] Modificar `collect.py` para salvar `destinatarioadvogados`
- [ ] Criar tabela `intimation_parties`
- [ ] Popular `intimation_lawyers` (atualmente vazia)
- [ ] Migrar dados existentes

### Sprint 2: Parser de Texto (3-4h)
- [ ] Criar `src/causaganha/parsing/lawyer_matcher.py`
- [ ] Implementar regex patterns para matching
- [ ] Calcular confidence score
- [ ] Testes unitários com casos reais

### Sprint 3: Pipeline Híbrido (4-5h)
- [ ] Modificar `analyze.py` para usar dados estruturados primeiro
- [ ] Criar prompt reduzido para casos com matching
- [ ] Manter prompt completo como fallback
- [ ] Logging de qual estratégia foi usada

### Sprint 4: Validação (2-3h)
- [ ] Reprocessar 100 decisões
- [ ] Comparar acurácia vs abordagem anterior
- [ ] Validar economia de tokens
- [ ] Ajustar thresholds de confidence

## 🎯 Casos de Uso

### Caso 1: Matching Perfeito (60%)
```
API:
  Partes: [A] JOÃO, [P] INSS
  Advogados: MARIA (RO1234), (sem oab)

Texto: "Advogado do AUTOR: MARIA - RO1234"
       "ADVOGADO DO RÉU: PROCURADORIA FEDERAL"

✅ Matching automático
→ LLM recebe dados estruturados
→ Prompt reduzido (800 tokens vs 2000)
```

### Caso 2: Matching Parcial (20%)
```
API:
  Partes: [A] MARIA, [P] EMPRESA XYZ
  Advogados: ADV1, ADV2, ADV3 (múltiplos)

Texto: Padrão não claro

⚠️ Matching incerto
→ LLM recebe dados estruturados como hint
→ Prompt médio (1200 tokens)
```

### Caso 3: Sem Matching (20%)
```
API:
  Partes: complexas
  Advogados: múltiplos sem padrão

❌ Matching falhou
→ LLM análise completa
→ Prompt full (2000 tokens)
```

## 🔬 Métricas de Sucesso

- [ ] Taxa de matching > 60%
- [ ] Acurácia mantida > 95%
- [ ] Economia de tokens > 50%
- [ ] Tempo de processamento < 1.5x atual
- [ ] Cobertura de casos edge

## 🚧 Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|-------|---------------|-----------|
| Parsing falha em casos edge | Média | Fallback para LLM completo |
| Dados API inconsistentes | Baixa | Validação + logs |
| Regex muito específico | Média | Múltiplos patterns + fuzzy matching |
| Overhead de complexidade | Baixa | Arquitetura em camadas clara |

## 📝 Exemplo de Código

```python
from causaganha.parsing.lawyer_matcher import match_lawyers_to_parties

async def analyze_with_hybrid_approach(intimation):
    # Camada 1: Dados estruturados
    structured_data = {
        "parties": intimation.destinatarios,
        "lawyers": intimation.destinatarioadvogados
    }

    # Camada 2: Parsing
    matching = match_lawyers_to_parties(
        texto=intimation.texto,
        lawyers=structured_data["lawyers"]
    )

    # Decisão de estratégia
    if matching.confidence > 0.80:
        # Prompt reduzido
        prompt = build_reduced_prompt(structured_data, matching)
        result = await llm.analyze(prompt)
    else:
        # Prompt completo com hints
        prompt = build_full_prompt_with_hints(
            texto=intimation.texto,
            hints=structured_data
        )
        result = await llm.analyze(prompt)

    return result
```

## ✅ Próximos Passos

1. **Hoje**: Implementar Sprint 1 (salvar dados estruturados)
2. **Amanhã**: Implementar Sprint 2 (parser)
3. **Depois de amanhã**: Sprint 3 (pipeline híbrido)
4. **Fim da semana**: Sprint 4 (validação)

## 📚 Referências

- API PJe: `/home/frank/workspace/djen.yml`
- Análise atual: 60% dos casos com padrão parseável
- Economia projetada: 60% de redução de custos
- Dados no banco: 5.794 decisões disponíveis
