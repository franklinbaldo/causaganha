# RFC 0001 — Diagnóstico da estratégia de fine-tuning do OPF (Decision Segmenter v7)

- **Status:** Proposto
- **Data:** 2026-06-10
- **Relacionado:** ADR 0010 (Rebuild Segmenter Pipeline v7)
- **Escopo:** estratégia de fine-tuning do OPF (token classifier BIOES de spans-âncora)
  para segmentação de decisões judiciais — dados gold, ontologia, treino, avaliação,
  inferência e CI.

## 1. Resumo executivo

A estratégia de fine-tuning v7 está **bem desenhada e parcialmente executada**.
A fundação é sólida: ontologia de 26 entradas consistente entre código, JSON,
testes e guideline; tooling de anotação com validação mecânica
(`opf_annotate.py`); seed gold de 20 documentos construído pelo fluxo de
subagentes com ensemble de verificação; e decisões de design corretas
(excluir `ref_normativa` do treino, âncoras curtas, regras anti-ambiguidade).

Porém, **não está "tudo certo"**. O estado atual tem três problemas que
invalidariam um treino sério hoje:

1. **`preliminar_inicio`/`preliminar_fim` existem apenas no test set** (0
   exemplos no train, 0 no val). O modelo é avaliado em categorias que nunca
   pôde aprender — F1 garantidamente 0, puxando o macro-F1 para baixo de forma
   espúria.
2. **O val set cobre só 17/25 categorias** (faltam `voto_*`,
   `acordao_decisorio_*`, `capitulo_merito_fim`, `custas_fim`, `preliminar_*`).
   Early stopping / seleção de checkpoint fica cega para 1/3 da ontologia —
   justamente as categorias novas da v7.
3. **Volume e diversidade insuficientes**: 20 docs, 189 spans, 1 tribunal
   (TJRO). Categorias raras têm 1–4 spans no corpus inteiro. Qualquer F1
   reportado nesse test set (3 docs) tem variância enorme e não generaliza.

Além disso, peças prometidas pelo ADR 0010 ainda não existem como código:
o ensemble de verificação 4-papéis não está versionado como script
reprodutível, e o pre-pass de `ref_normativa` existe mas não está integrado
a nenhum pipeline de inferência.

**Recomendação central:** não treinar um modelo "para valer" com o seed atual.
Tratar o seed como prova do método (que funcionou) e executar a Fase 2 de
escala com as correções de desenho abaixo — em particular, **estratificar os
splits por categoria, não só por tipo de documento**, e definir critérios
quantitativos de "pronto para treinar" (gates de suporte mínimo por classe).

## 2. Estado atual (o que existe e funciona)

| Componente | Estado | Evidência |
|---|---|---|
| Ontologia v7 (26 entradas: `O` + 5 single-anchor + 20 pareadas) | ✅ consistente | `label_space.json`, `SPAN_CLASS_NAMES_V7`, `tests/test_privacy_filter_segmenter.py` (teste empírico código↔JSON↔gold) |
| Guideline de anotação | ✅ boa | `data/segmenter_splits/annotation_guideline_v7.md` — âncoras curtas, regras de dispositivo único, anti-patterns |
| Tooling de anotação | ✅ sólido | `scripts/opf_annotate.py` (`validate`/`from-spans`/`preview`) — falha alto em offset/overlap/whitespace |
| Seed gold | ✅ commitado | 20 docs TJRO (8 acórdãos, 12 sentenças), 189 spans, `test_verified_by = prompt_ensemble:strict+disambig+blind+adversarial` |
| Exclusão de `ref_normativa` do treino | ✅ correta | regex pre-pass em `scripts/ref_normativa_prepass.py`; evita inflação de macro-F1 da v6 |
| Reconstrução de regiões | ✅ implementada | `scripts/reconstruct_regions.py` (`pair_inicio_fim`, tiling single-anchor) |
| Orquestração de treino/eval | ✅ implementada | `scripts/train_decision_segmenter.py` (subprocess OPF, valida splits antes, reporta F1 com/sem ref_normativa) |
| CI de dados | ✅ parcial | `.github/workflows/train-segmenter.yml` valida os 3 splits com `opf_annotate.py validate` + label space |
| Atribuição de modelos em camadas (Haiku rotula, Sonnet verifica) | ✅ usada no seed | manifest (`labeler`, `verifier_model`); decorrelação de erros é o ponto do ensemble |

O método do seed — amostragem estrita, subagentes Haiku devolvendo
`{category, match, nth}` com match único mais curto, offsets resolvidos por
`from-spans`, verificação Sonnet em val+test — **funcionou** e deve ser
mantido para a escala. Isso o ADR 0010 já estabelece; este RFC não propõe
mudar o método, e sim corrigir o desenho dos dados e fechar lacunas de
infraestrutura.

## 3. Diagnóstico — o que está faltando ou errado

### 3.1 🔴 Crítico: categorias declaradas mas não-aprendíveis

Cobertura medida nos splits commitados (categorias não-`O` = 25):

| Split | Docs | Spans | Cobertura | Faltando |
|---|---|---|---|---|
| train | 14 | 124 | 23/25 | `preliminar_inicio`, `preliminar_fim` |
| val | 3 | 31 | **17/25** | `voto_*`, `acordao_decisorio_*`, `capitulo_merito_fim`, `custas_fim`, `preliminar_*` |
| test | 3 | 34 | 23/25 | `custas_inicio`, `custas_fim` |

Consequências concretas:

- **`preliminar_*` só no test**: o modelo será penalizado em algo que não viu
  no treino. Isso é exatamente o cenário que o ADR 0010 manda evitar
  ("Categories that cannot be populated should be trimmed rather than
  declared empty") — a promessa está **não cumprida** no artefato commitado.
- **Val cego para as 4 categorias novas de acórdão** (`voto_*`,
  `acordao_decisorio_*`): a razão de ser da extensão 22→26 classes não é
  observável durante o treino. Seleção de checkpoint pode escolher um modelo
  pior nessas classes sem que ninguém perceba.
- **`custas_*` ausente do test**: F1 de custas não é mensurável no test set.

A causa-raiz é que o split foi estratificado por **tipo de documento**
(acórdão/sentença), não por **cobertura de categoria**. Com 3 docs em
val/test, é estatisticamente esperado que classes raras caiam fora.

### 3.2 🔴 Crítico: escala e poder estatístico

- 1 tribunal (TJRO). Cabeçalhos, fórmulas de encerramento e formatação de
  caderno variam por tribunal; um modelo treinado só em TJRO aprenderá os
  *templates* do TJRO, não os conceitos.
- Classes raras com 1–4 spans no corpus inteiro (`preliminar_*: 1+1`,
  `custas_fim: 2`, `acordao_decisorio_fim: 2`, `voto_*: 3+3`). Nenhum F1
  por classe é significativo nesse regime.
- Test set de 3 documentos: um único documento errado move o macro-F1 em
  dezenas de pontos. Não dá para comparar v7 vs. v6 ou run A vs. run B.

### 3.3 🟠 Alto: promessas do ADR sem código versionado

- **Ensemble de verificação 4-papéis** (strict-boundary, disambiguation,
  blind-relabel, adversarial): declarado no manifest, mas não há script ou
  prompt versionado no repo. Hoje o ensemble não é **reproduzível** — quem
  for escalar a anotação terá que reinventá-lo, com risco de divergir do que
  validou o seed.
- **Re-adjudicação de ambíguos por modelo forte**: regra do ADR sem
  artefato correspondente.
- **`ref_normativa` pre-pass não integrado**: `extract_ref_normativa` +
  `merge_with_opf_spans` existem, mas nenhum pipeline de inferência os chama.
  Sem inferência ponta-a-ponta (OPF → merge regex → `reconstruct_regions`),
  o valor do modelo não é entregável.

### 3.4 🟠 Alto: avaliação sem gates nem profundidade

- CI valida formato dos dados, mas **não há gate quantitativo**: nada impede
  commitar um gold com categoria zerada (foi o que aconteceu) nem regressão
  de macro-F1 entre treinos.
- Sem avaliação por tribunal (impossível hoje, mas precisa existir quando
  houver multi-tribunal), sem matriz de confusão por categoria, sem análise
  de erro de **fronteira** vs. erro de **categoria** (para âncoras curtas,
  são modos de falha muito diferentes).
- `reconstruct_regions.py` e `merge_with_opf_spans` não têm testes de
  integração sobre o gold — a métrica que importa para o produto é a
  **região reconstruída**, não o span-âncora, e ela não é medida em lugar
  nenhum.

### 3.5 🟡 Médio: higiene de repositório

- `README.md` ainda anuncia "22-class judicial token classifier" (v5/v6);
  deveria dizer 26 entradas / v7.
- Notebooks legados (`train_privacy_filter.py` marimo,
  `train_decision_segmenter.ipynb`) usam taxonomia e base antigas
  (BERTimbau + BIO), divergindo do caminho OPF real
  (`train_segmenter_colab.ipynb` → scripts). Confundem quem chega no repo.
- `scripts/test_opf_label_space.py` (contrato "O-first") não roda em CI.
- Scripts v5 (`bootstrap_training_corpus.py`, `augment_segmenter_data.py`)
  sem marcação de deprecated.

## 4. Proposta

### 4.1 Princípios

1. **Não treinar para valer com o seed.** O seed prova o método; o modelo
   v7 "oficial" só nasce depois do gold escalado passar nos gates abaixo.
2. **Estratificar splits por categoria, não por tipo de documento.** O
   sampler da Fase 2 deve garantir cobertura por split, não só no agregado.
3. **Gates quantitativos como código, não como prosa.** As regras do ADR
   viram asserções que a CI executa.

### 4.2 Gates de "pronto para treinar" (propostos)

Adicionar ao `prepare_privacy_filter_dataset.py` (modo promote) e à CI:

| Gate | Regra |
|---|---|
| G1 — cobertura | toda categoria do `label_space.json` tem ≥ 1 exemplo em **cada** split (train, val, test) |
| G2 — suporte mínimo | toda categoria tem ≥ **10** spans no train e ≥ **3** em val e em test |
| G3 — trim obrigatório | categoria que não atingir G1/G2 após a rodada de escala é **removida do label space** antes do treino (regra do ADR, agora executável) |
| G4 — diversidade | ≥ **3 tribunais** e ambos os tipos de documento em cada split |
| G5 — volume | ≥ **150 documentos** no total (~100/25/25), priorizando acórdãos e docs com `preliminar`/`custas`/`honorarios` |

Números de G2/G5 são pontos de partida deliberadamente modestos (regime
few-shot de fine-tuning de token classifier); revisar após a primeira rodada
de eval.

### 4.3 Plano de execução (Fase 2 revisada)

**Etapa A — corrigir o desenho antes de escalar (sem anotação nova):**
1. Implementar gates G1–G5 como checagens em
   `prepare_privacy_filter_dataset.py` + job de CI (falha alto; o seed atual
   deve falhar G1/G2/G4/G5 — isso é o comportamento esperado e documenta a
   dívida).
2. Versionar o ensemble de verificação: prompts dos 4 papéis + orquestração
   em `scripts/` (ou `docs/` se permanecer fluxo de subagente manual), com a
   regra de re-adjudicação de ambíguos. Critério: outra pessoa reproduz a
   verificação do seed sem perguntar nada.
3. Mover `preliminar_*` do test para o train **ou** (preferível) deixar como
   está e resolver via Etapa B — não treinar nesse meio-tempo.

**Etapa B — escalar o gold (método do ADR, sampler corrigido):**
4. Amostragem dirigida por categoria: minerar candidatos por regex barata
   ("PRELIMINAR", "Das custas", "ACORDAM", "É o voto") nos cadernos IA para
   garantir suporte das classes raras, em vez de amostragem uniforme.
5. 3–5 tribunais além do TJRO (sugestão: ao menos um TJ grande tipo
   TJSP/TJMG, um TRF e uma Turma Recursal, para variar template e instância).
6. Split estratificado por categoria (greedy: aloca documentos a splits
   minimizando categorias descobertas), tipo de documento e tribunal.
7. Rodar ensemble de verificação versionado em val+test; atualizar manifest.

**Etapa C — fechar o loop de inferência e avaliação:**
8. Pipeline de inferência ponta-a-ponta: OPF → `merge_with_opf_spans`
   (ref_normativa) → `reconstruct_regions` → JSON de regiões; com testes de
   integração sobre o gold.
9. Eval em dois níveis: F1 de span-âncora (atual) **e** F1/IoU de região
   reconstruída (métrica de produto). Reportar por categoria, por tribunal e
   por tipo de documento; macro-F1 com e sem `ref_normativa` (como o ADR já
   pede).
10. Gate de regressão: treino só "promove" modelo se macro-F1 (sem
    ref_normativa) ≥ melhor anterior − ε, com artefato de métricas
    commitado/anexado ao run.

**Etapa D — higiene:**
11. Atualizar README (26 entradas, v7, fluxo Colab→scripts).
12. Marcar notebooks/scripts v5 como deprecated (ou mover para
    `experiments/archive/`).
13. Incluir `scripts/test_opf_label_space.py` no job de CI (CPU, ~2 min).

### 4.4 Fora de escopo deste RFC

- Trocar o modelo-base do OPF ou o esquema BIOES/banded attention — sem
  evidência de problema; só reavaliar com eval da Etapa C em mãos.
- Aumentação sintética de dados (`augment_segmenter_data.py` é v5; decidir
  depois da primeira rodada real de eval, se classes raras continuarem
  fracas mesmo com amostragem dirigida).

## 5. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Amostragem dirigida por regex enviesa o gold para documentos "fáceis de achar" | manter fração de amostragem uniforme (~30%) em cada rodada |
| Classes raras continuarem raras mesmo com mineração (ex.: `preliminar_fim` genuinamente incomum) | aplicar G3: cortar do label space e documentar no ADR, em vez de manter classe morta |
| Custo de anotação multi-tribunal | método em camadas já mitiga (Haiku rotula, Sonnet só verifica val+test); escalar por rodadas de ~30 docs |
| Ensemble versionado divergir do que validou o seed | reconstruí-lo a partir do manifest + re-verificar o próprio seed como teste de fumaça |

## 6. Decisão solicitada

1. Aprovar os gates G1–G5 (e calibrar os números).
2. Aprovar a ordem Etapa A → B → C → D, com "nenhum treino oficial antes de
   G1–G5 verdes" como regra.
3. Decidir o conjunto de tribunais-alvo da primeira rodada de escala.
