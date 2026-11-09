---
name: jurimetria
description: >-
  Guia metodológico e framework de auditoria para jurimetria empírica e modelagem de
  decisões judiciais brasileiras (CPC, CPP, DataJud, DJEN). Use esta skill sempre que
  projetar, auditar ou refinar pipelines de extração, classificação de desfecho
  processual, resolução de valor/sucumbência, atribuição de polos/advogados e métricas
  de sucesso semântico em dados judiciais.
---

# Skill de Jurimetria Empírica e Modelagem Processual Brasileira

Esta skill estabelece os fundamentos teóricos, metodológicos e computacionais para a
engenharia de jurimetria no Brasil, com foco em dados do Diário de Justiça Eletrônico Nacional (DJEN)
e do Conselho Nacional de Justiça (DataJud/Resoluções CNJ).

Ela serve como manual de melhores práticas e como **instrumento de auditoria contínua**
para assegurar que os modelos do projeto não degradem a complexidade jurídica em binários
simplistas ("ganhou/perdeu") e operem com máxima eficiência computacional (zero custo de API e alta vazão em CPU).

---

## 1. Princípios Fundamentais da Jurimetria

### 1.1. O Espaço de Rótulos é Ortogonal, Não Binário
Reduzir uma decisão judicial a um rótulo ingênuo de "vitória vs. derrota" é um erro de constructo:
1. **Juízo de Admissibilidade vs. Juízo de Mérito (CPC art. 485 vs. art. 487):**
   - Extinção sem resolução de mérito (ilegitimidade, inépcia, litispendência, perempção) é uma decisão *terminativa*, não improcedência.
2. **Efeito Substitutivo e Inversão de Polaridade Recursal (CPC art. 1.008):**
   - A decisão de 2º grau julga o **recurso**, não diretamente o pedido originário.
   - Um acórdão que dá *provimento* ao recurso do réu reverte a sentença e consagra a vitória da defesa.
   - Um acórdão que *nega provimento* ao recurso do réu confirma a vitória do autor.
3. **Parcial Procedência e Sucesso Proporcional:**
   - Na esmagadora maioria das demandas indenizatórias e cíveis, há sucumbência recíproca.
   - O indicador empírico real é a **Taxa de Êxito Substantivo**:
     $$\text{Taxa de Sucesso do Autor} = \frac{\text{Valor da Condenação}}{\text{Valor da Causa / Pedido}}$$
   - Exemplo: Pedido de R$ 100.000,00 com condenação em R$ 2.000,00 representa **98% de êxito para a defesa** e apenas 2% para o autor, embora a decisão seja formalmente "procedente em parte".

---

## 2. A Arquitetura em Duas Camadas

Para manter o modelo de extração preciso e rápido, desacople a representação textual da regra de negócio:

```
[ Publicação do DJEN ]
          │
          ▼
┌────────────────────────────────────────────────────────┐
│  CAMADA 1: Extração Semântica Fiel ao Texto / CPC      │
│  - Natureza: Sentença, Acórdão, Interlocutória, Desp.  │
│  - Comando: PROCEDENTE, EXTINTO ART. 485, PROVIDO...   │
│  - Valores: Condenação Principal, Causa, Honorários %  │
│  - Sujeitos: Partes (DJEN), Advogados (OAB), Juiz (NER)│
└────────────────────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────┐
│  CAMADA 2: Interpretação Contextual de Sucesso         │
│  - Resolução do Polo Vencedor (WinnerPolo = A | P)     │
│  - Cálculo de Taxa de Redução de Passivo (Defesa)      │
│  - Atribuição Determinística do Advogado Vencedor      │
│  - Indicadores de Eficácia Processual por Tribunal     │
└────────────────────────────────────────────────────────┘
```

---

## 3. Matriz de Classificação Processual (Camada 1)

Consulte o mapeamento normativo detalhado em:
[Taxonomia Processual CPC e Dispositivos de Julgamento](./references/taxonomia_processual_cpc.md)

| Classe Processual | Vocabulário Dispositivo Nativo | Interpretação no Negócio |
| :--- | :--- | :--- |
| **Mérito Pleno** | `PROCEDENTE` | Acolhimento integral da pretensão autoral |
| **Mérito Parcial** | `PARCIALMENTE_PROCEDENTE` | Sucumbência recíproca; requer medição econômica |
| **Rejeição de Mérito** | `IMPROCEDENTE` | Vitória da tese defensiva do réu (coisa julgada material) |
| **Terminativa** | `EXTINTO_SEM_RESOLUCAO_MERITO` | Vitória processual da defesa; sem coisa julgada material |
| **Transacional** | `HOMOLOGACAO_ACORDO` | Resolução consensual; sem sucumbência formal |
| **Tutela Provisória** | `TUTELA_DEFERIDA` / `TUTELA_INDEFERIDA` | Medida de urgência/evidência; incidente cognitivo |
| **Recursal** | `PROVIDO` / `NAO_PROVIDO` / `PARCIALMENTE_PROVIDO` | Modificação ou manutenção da decisão inferior |
| **Inadmissibilidade** | `NAO_CONHECIDO` / `PREJUDICADO` | Vício formal recursal (intempestividade, preparo, etc.) |

---

## 4. Governança e Soberania dos Metadados do DJEN

1. **Partes e Polos:** `destinatarios` (`polo: "A"` ou `"P"`, CPF/CNPJ) do DJEN são a fonte da verdade. O NLP faz *grounding* e desambiguação, nunca suposição.
2. **Advogados e OAB:** `destinatarioadvogados` vinculam a OAB ao respectivo polo. O cruzamento entre `WinnerPolo` e o metadado determina `winner_lawyer_oab` sem alucinação.
3. **Número CNJ:** `numero_processo` no metadado dita o `PROCESSO_PRINCIPAL`. Qualquer outro CNJ no texto é catalogado como `PROCESSO_CITADO` ou `PROCESSO_PARADIGMA`.
4. **Magistrado / Relator:** O DJEN **não** fornece o nome do magistrado; a responsabilidade de extração é 100% do NER via assinatura no `ENCERRAMENTO`.

---

## 5. Roteiro de Auditoria de Jurimetria

Para auditar um pipeline ou base de dados em relação às melhores práticas de jurimetria:

1. **Execute o script de auditoria automatizada:**
   ```powershell
   uv run python .agents/skills/jurimetria/scripts/audit_jurimetrics_compliance.py
   ```
2. **Valide a checklist metodológica:**
   Consulte a [Checklist de Auditoria de Jurimetria](./references/auditoria_checklist.md) para verificar:
   - Resolução de efeito substitutivo de recursos.
   - Preservação de granularidade de tutelas provisórias e extinções preliminares.
   - Prevenção de vazamento de dados em séries temporais judiciais (temporal split vs. random split).
   - Eficiência computacional (> 200 doc/s em CPU, zero API cost).
