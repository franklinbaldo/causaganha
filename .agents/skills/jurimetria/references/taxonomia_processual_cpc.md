# Referência Técnica: Taxonomia Processual Civil Brasileira e Dispositivos

Este documento formaliza as categorias normativas do Código de Processo Civil (Lei 13.105/2015)
e da Lei dos Juizados Especiais (Lei 9.099/1995) que devem ser preservadas pelo pipeline
de jurimetria, evitando colapsos semânticos.

---

## 1. Sentenças de Mérito (CPC, Art. 487)

Haverá resolução de mérito quando o juiz:
- **Art. 487, I:** Acolher ou rejeitar o pedido do autor (`PROCEDENTE`, `PARCIALMENTE_PROCEDENTE`, `IMPROCEDENTE`).
- **Art. 487, II:** Decidir, de ofício ou a requerimento, sobre a ocorrência de `DECADENCIA` ou `PRESCRICAO`.
- **Art. 487, III:** Homologar:
  - `a)` o reconhecimento da procedência do pedido;
  - `b)` a transação (`HOMOLOGACAO_ACORDO`);
  - `c)` a renúncia à pretensão formulada.

### Implicações Jurimétricas
- Produz coisa julgada material (`res judicata`), impedindo a repropositura da mesma ação com mesmas partes, causa de pedir e pedido.
- `PARCIALMENTE_PROCEDENTE` exige análise econômica: a vitória teórica do autor pode mascarar vitória fática da defesa caso o valor concedido seja marginal em relação ao pedido inicial.

---

## 2. Sentenças Terminativas / Sem Resolução de Mérito (CPC, Art. 485)

O juiz não resolverá o mérito quando:
- **Inc. I:** Indeferir a petição inicial.
- **Inc. II:** O processo ficar parado por mais de 1 ano por negligência das partes.
- **Inc. III:** Por não promover os atos que lhe competir, o autor abandonar a causa por mais de 30 dias.
- **Inc. IV:** Verificar a ausência de pressupostos de constituição e desenvolvimento válido e regular do processo.
- **Inc. V:** Reconhecer a existência de perempção, litispendência ou coisa julgada.
- **Inc. VI:** Verificar ausência de legitimidade ou de interesse processual (`ILEGITIMIDADE_PASSIVA`, `FALTA_INTERESSE_AGIR`).
- **Inc. VII:** Acolher alegação de existência de convenção de arbitragem.
- **Inc. VIII:** Homologar a desistência da ação.
- **Inc. IX:** Em caso de morte do réu em ação intransmissível.

### Implicações Jurimétricas
- Rótulo nativo: `EXTINTO_SEM_RESOLUCAO_MERITO`.
- Não faz coisa julgada material (permite repropositura caso sanado o vício, salvo perempção/coisa julgada).
- Na jurimetria de contencioso de massa (bancos, telefonia, varejo), a extinção sem mérito por ilegitimidade ou inépcia é uma **vitória tática da defesa**, que reduz custos judiciais sem pagamento de indenizações.

---

## 3. Tutelas Provisórias (CPC, Arts. 294 a 311)

Pronunciamentos interlocutórios cognitivos proferidos com base em cognição sumária:
- **Tutela de Urgência (Art. 300):** Probabilidade do direito (*fumus boni iuris*) e perigo de dano ou risco ao resultado útil (*periculum in mora*).
  - Rótulos: `TUTELA_DEFERIDA`, `TUTELA_INDEFERIDA`, `TUTELA_PARCIAL`.
- **Astreintes (Art. 537):** Multa cominatória diária para forçar o cumprimento de obrigação de fazer/não fazer.
  - O NER deve extrair `VALOR_ASTREINTES_MULTA` e sua periodicidade (ex.: R$ 500/dia até o limite de R$ 20.000,00).

---

## 4. O Sistema Recursal e a Dinâmica de Polos (CPC, Arts. 994 a 1.044)

Nos recursos ordinários (Apelação, Agravo de Instrumento, Recurso Inominado nos JEFs), o julgamento possui:
1. **Juízo de Admissibilidade:**
   - Preenchimento de requisitos intrínsecos (cabimento, legitimidade, interesse) e extrínsecos (tempestividade, preparo, regularidade formal).
   - Rótulos: `CONHECIDO` vs. `NAO_CONHECIDO` / `PREJUDICADO`.
2. **Juízo de Mérito Recursal:**
   - Análise do inconformismo com a decisão atacada.
   - Rótulos: `PROVIDO`, `NAO_PROVIDO`, `PARCIALMENTE_PROVIDO`.

### Regra do Efeito Substitutivo (CPC, Art. 1.008)
O julgamento proferido pelo tribunal substitui a decisão impugnada no que tiver sido objeto de recurso.

**Tabela da Inversão de Polaridade:**
| Recorrente (`recorrente_polo`) | Decisão do Recurso | Decisão Substitutiva Final | Vencedor Substantivo (`WinnerPolo`) |
| :--- | :--- | :--- | :--- |
| Autor (`A`) | `PROVIDO` | Reforma sentença desfavorável | **Autor (`A`)** |
| Autor (`A`) | `NAO_PROVIDO` | Mantém sentença desfavorável | **Réu (`P`)** |
| Réu (`P`) | `PROVIDO` | Reforma sentença favorável ao autor | **Réu (`P`)** |
| Réu (`P`) | `NAO_PROVIDO` | Mantém condenação do réu | **Autor (`A`)** |

---

## 5. Particularidades dos Juizados Especiais Cíveis (Lei 9.099/1995)

- **Art. 38:** Dispensa do relatório formal. A sentença abre diretamente na fundamentação ("Vistos. Dispensado o relatório..."). O segmentador estrutural deve reconhecer essa tipologia e não descartar o documento por ausência de seção explícita de relatório.
- **Art. 40:** Decisão elaborada por Juiz Leigo e submetida à homologação do Juiz de Direito togado. O extrator de magistrado deve capturar tanto o prolator leigo quanto o togado homologador.
- **Art. 55:** Em 1º grau não há condenação em custas e honorários sucumbenciais (salvo litigância de má-fé). No 2º grau (Turma Recursal), o recorrente vencido paga honorários de 10% a 20%.
