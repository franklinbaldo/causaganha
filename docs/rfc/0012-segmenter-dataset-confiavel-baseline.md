# RFC 0012 — Segmentador v8: dataset confiável e baseline honesto com dados reais

- **Status:** Proposto
- **Data:** 2026-07-17
- **Depende de:** RFC 0001 (segmenter v7 finetuning/diagnóstico), RFC 0003 (JURIS TJRO
  como fonte de documentos reais)
- **Relação com RFC 0011 / PR #831 / PR #832:** esta RFC **substitui a fundação** do
  plano sintético. A RFC 0011 (gerador sintético) deixa de ser a base do segmentador e
  passa a ser a **camada experimental** (§15, PR 4), condicionada à existência do
  baseline real desta RFC. O PR #832 não deve ser mergeado como está; seus ativos são
  reaproveitados conforme o mapa de disposição em §18.

## 1. Resumo executivo

O CausaGanha precisa de um modelo que identifique âncoras estruturais em decisões
judiciais brasileiras: cabeçalhos, limites de seção, conclusões operativas (dispositivo,
resultado), custas, honorários, referências legais e marcadores de decisão colegiada.

O objetivo desta RFC **não é o maior F1 possível**. É produzir um resultado cuja
linhagem de dados, qualidade de anotação, integridade de splits e procedimento de
avaliação sejam fortes o suficiente para que **o F1 reportado signifique o que aparenta
significar**. Só depois desse baseline existir o projeto otimiza geração sintética,
misturas de treino e generalização mais ampla.

## 2. Problema

O fluxo atual (culminando no PR #832) mistura preocupações que precisam ser separadas:

- extração heurística de candidatos;
- anotação;
- correção de anotação;
- promoção a "gold";
- gestão de splits;
- geração sintética;
- diagnósticos de qualidade;
- treino;
- seleção de checkpoint;
- avaliação;
- publicação de release.

Como essas preocupações estão combinadas, três falhas já ocorreram de fato (todas
documentadas no próprio PR #832 e na sua rodada de review):

1. **Dados mecanicamente válidos foram descritos como "gold".** `promote_gold()`
   publica o que estiver nos splits; não existe escada candidato → anotado → adjudicado.
   Volume provisório satisfez silenciosamente o gate de avaliação.
2. **Dados de avaliação provisórios influenciaram a seleção de modelo.** O split de
   teste foi avaliado a cada época e o checkpoint (época 14, F1 0.567) foi escolhido
   pelo melhor F1 *de teste* — o número publicado é uma estatística de seleção, não uma
   estimativa não-enviesada. Além disso, docs de val/test das rodadas E/F foram
   anotados a partir de predições do próprio modelo (rodada E) ou de rascunhos de LLM
   (rodada F), violando qualquer padrão de independência.
3. **Testes de software foram confundidos com evidência de qualidade de anotação ou de
   modelo.** 900+ testes verdes validam o código dos guardrails, não a correção
   semântica dos rótulos.

O novo sistema deve tornar explícitos: o **estado** do dataset, a **confiança** da
anotação e a **elegibilidade** para avaliação.

## 3. Princípios de produto

### 3.1 Uma garantia de qualidade só existe se estiver registrada, nunca por sobrescrita

Um documento carrega três tipos de artefato que **coexistem**, não uma cadeia de
estados que se substituem: o registro de **documento** original (texto-fonte +
proveniência + rótulos propostos por extração heurística) nunca é apagado nem
reescrito; cada **anotação** é um registro adicional que referencia o `document_id`; a
**adjudicação/review** é outro registro adicional que referencia as anotações que
resolve. A garantia de um documento em um dado momento é lida pelo conjunto de
registros presentes para aquele `document_id` — "adjudicado" significa "existe um
registro de review aceito para este documento", não "o documento foi movido para uma
pasta `reviews/`".

`split-assigned` e `released` **não são artefatos por documento** — são propriedades de
uma *build* de dataset, registradas exclusivamente no manifest de split e no manifest
de release dentro de `dataset-releases/<release-id>/` (§8), nunca inferidas da
localização de um arquivo. Um documento nunca é "promovido": o que muda é qual manifest
o referencia, e com qual conjunto de anotações e reviews resolvidos naquele momento
esse manifest foi construído.

Nenhuma alegação de qualidade pode ser feita por inferência de diretório ou de nome de
arquivo — sempre pela presença do registro correspondente.

### 3.2 Validade mecânica não é correção semântica

Um registro pode ter JSON válido, offsets válidos e categorias válidas e ainda conter
rótulos errados. Validação mecânica e revisão de qualidade de anotação permanecem
separadas.

### 3.3 O teste é avaliado uma única vez

O split de teste **não pode** ser usado para:

- seleção de época;
- seleção de hiperparâmetros;
- mudanças de ontologia;
- refinamento de prompt;
- mudanças de guideline de anotação;
- ajuste de gerador sintético;
- calibração de threshold.

Seleção de checkpoint usa **exclusivamente métricas de validação**.

### 3.4 Dados reais estabelecem o baseline

O primeiro baseline de produção usa apenas documentos reais: treino no estado
**anotado**, validação e teste no estado **adjudicado** (duas anotações independentes +
adjudicação — política completa no §9). Treino nunca precisa alcançar "adjudicado";
exigir isso do treino contradiria o próprio §9, que aceita uma anotação completa +
spot-review de risco para dados de treino. Dados sintéticos, aumentados e híbridos são
fontes experimentais: só entram no treino via ablações controladas **depois** do
baseline real estar congelado.

### 3.5 Todo waiver é estreito

Um waiver de diversidade de tribunal não pode desabilitar salvaguardas não
relacionadas. Cada regra de prontidão tem status independente e waiver
independentemente configurável, com justificativa registrada. Não existe
`--skip-gates` genérico (a versão all-or-nothing do PR #832 é exatamente o
antipadrão que este princípio proíbe).

## 4. Objetivos do primeiro release

- definir uma ontologia canônica (decisão em §5);
- construir um corpus real anotado (treino) e adjudicado (validação/teste), com o gate
  de referência humana do §9.1 antes de qualquer split ser nomeado `gold`;
- prevenir vazamento exato e por quase-duplicata entre splits;
- congelar validação e teste **antes** de qualquer experimentação de modelo;
- treinar um baseline reprodutível só com dados reais;
- selecionar checkpoints exclusivamente por métricas de validação;
- avaliar o checkpoint congelado **uma vez** no teste trancado;
- publicar manifests imutáveis de dataset e modelo;
- tornar toda alegação de qualidade rastreável a código ou evidência de revisão.

## 5. Decisões pré-fixadas (para não serem tomadas durante a implementação)

Estas decisões condicionam tudo que vem depois e ficam registradas aqui, não em
discussão de PR:

1. **Ontologia v8 = ontologia v7 congelada, versionada por semver
   (`segmenter-ontology-v8.0.0`).** `ref_normativa` permanece fora do espaço treinável
   (RFC 0001: pré-passe regex na inferência). A ambiguidade conhecida do heading de
   `preliminar` ("1. PRELIMINARES" vs "PRELIMINAR REJEITADA" como palavra de resultado)
   é tratada na guideline de anotação, não na ontologia. Mudanças futuras seguem uma
   análise de migração explícita — não uma invalidação geral automática:
   - **adicionar categoria** (minor): anotações existentes continuam válidas; documentos
     antigos simplesmente não têm rótulo para a categoria nova até revisitados por
     spot-review de risco (§9);
   - **remover categoria** (major): invalida só os rótulos daquela categoria nos
     registros existentes — os demais rótulos do mesmo documento continuam válidos;
   - **renomear categoria sem mudar semântica** (minor): remapeamento mecânico
     determinístico, sem nova rodada de anotação;
   - **redefinir a semântica de uma categoria existente** (major): tratado como
     remoção + adição — invalida os rótulos daquela categoria e exige nova anotação
     só para ela;
   - **mudança de guideline sem mudança de schema** (bump de `guideline_version`,
     independente de `ontology_version`): não invalida anotações por padrão; dispara
     spot-review de risco (§9) sobre uma amostra dos registros anotados sob a versão
     anterior antes de qualquer decisão de invalidação seletiva.
   Mudanças major exigem registro nesta RFC ou em RFC sucessora; mudanças minor podem
   ser decididas pelo mantenedor do dataset e registradas no manifest de release.
2. **O split de teste v7 atual está queimado.** Foi avaliado a cada época no PR #832 e
   suas expansões usaram rascunhos de modelo. Pelo §3.3, ele é agora **dado de
   desenvolvimento** — pode virar validação, nunca teste. O teste v8 vem de documentos
   **nunca tocados** por nenhuma sessão anterior (nota: os parquets
   `2017-07-ACORDAO` e `2023-09-SENTENCA` do JURIS já foram gastos pelas rodadas E/F).
3. **Independência de anotadores-LLM (definição operacional).** Neste projeto os
   anotadores são agentes LLM. Duas anotações são independentes **somente se**:
   produzidas por famílias de modelo distintas *ou* por execuções comprovadamente
   isoladas; nenhuma semeada com a saída da outra nem com qualquer predição do
   segmentador; e a configuração da execução (modelo, prompt/guideline, seed quando
   houver) registrada no próprio registro de anotação. Um "passe de correção" sobre um
   rascunho de modelo **não é** uma anotação independente.
4. **Metas de suprimento do primeiro release:** ≥ 150 docs de treino **anotados**
   (§9 — não "adjudicados"; ver §10 para a política de elegibilidade de split por
   estado mínimo), ≥ 30 de validação **adjudicados**, ≥ 30 de teste **adjudicados**,
   com suporte mínimo por categoria herdado do gate G2 vigente (≥ 10 ocorrências por
   categoria treinável no treino; ≥ 5 em validação para reportar métrica por
   categoria). Val/test custam ~3× o treino (duas anotações independentes +
   adjudicação); a meta é deliberadamente modesta.
5. **Métrica primária de seleção de checkpoint, declarada antes do treino:**
   **macro-F1 de validação sobre as categorias treináveis.** Desempate documentado:
   menor época (menos exposição a overfitting); persistindo empate, menor val loss.

## 6. Não-objetivos do primeiro release

Explicitamente adiados (viram Fase 5+, sob a RFC 0011 revisada):

- geração de documentos sintéticos;
- documentos híbridos real/sintético;
- juízes LLM de estilo;
- curriculum learning;
- composição estática de pesos por fonte (`compose_mix`);
- promoção automatizada a gold;
- representatividade nacional;
- anotação assistida por modelo de dados de validação ou teste;
- orquestração multi-provider de treino além de um runner reprodutível.

## 7. Papéis

- **Mantenedor do dataset** — extrai documentos candidatos, coordena anotação, adjudica
  conflitos, cria releases.
- **Desenvolvedor de modelo** — treina contra releases imutáveis e seleciona
  configurações por resultados de validação.
- **Revisor** — verifica qualidade de anotação, integridade de splits, proveniência e
  metodologia de avaliação.
- **Consumidor de produção** — carrega um modelo com ontologia documentada, linhagem de
  dataset e escopo de avaliação conhecido.

## 8. Artefatos canônicos

Diretórios separados por **tipo de artefato**, não por estado — um documento aparece em
`documents/` e, à medida que trabalho é feito sobre ele, também em `annotations/` e
depois em `reviews/`, sem que o registro original em `documents/` seja alterado ou
removido (§3.1). `dataset-releases/<release-id>/` não contém cópias de documentos
"promovidos"; contém manifests que referenciam `document_id`s por hash:

```text
data/segmenter/
  documents/                       # registros imutáveis, nunca movidos ou reescritos
  annotations/                     # um ou mais registros por document_id
  reviews/                         # adjudicação; ausente para a maioria do treino (§9)
  dataset-releases/
    <release-id>/
      split_manifest.json          # split-assignment desta build (§10) — não um
                                    # estado do documento, um artefato da build
      manifest.json                # manifest final imutável, só existe após
                                    # build_gold_release (§12)
```

### Registro de documento

```json
{
  "document_id": "stable-id",
  "text": "...",
  "proposed_labels": [],
  "source": {
    "system": "tjro_juris",
    "tribunal": "TJRO",
    "document_type": "sentenca",
    "source_uri": "...",
    "source_hash": "..."
  },
  "extraction": {
    "method": "boundary_phrase_extractor",
    "version": "..."
  }
}
```

### Registro de anotação

```json
{
  "document_id": "stable-id",
  "annotator_id": "annotator-or-agent-run",
  "annotator_config": {
    "model_family": "...",
    "guideline_version": "segmenter-v8-guideline-1",
    "seeded_with": "none"
  },
  "labels": [],
  "completed_at": "...",
  "annotation_method": "independent_full_read"
}
```

`seeded_with` só admite `"none"` para anotações que contam como independentes (§5.3).

### Registro de review (adjudicação)

```json
{
  "document_id": "stable-id",
  "status": "accepted",
  "final_labels": [],
  "reviewers": ["reviewer-a", "reviewer-b"],
  "resolution": "agreement-or-adjudication",
  "notes": [],
  "approved_at": "..."
}
```

### Manifest de release de dataset

```json
{
  "release_id": "segmenter-real-v8.1",
  "ontology_version": "segmenter-ontology-v8.0.0",
  "guideline_version": "segmenter-v8-guideline-1",
  "source_commit": "full-git-sha",
  "dependency_lock_hash": "sha256-of-pinned-lockfile",
  "split_hashes": { "train": "...", "validation": "...", "test": "..." },
  "counts": {},
  "tribunals": {},
  "document_types": {},
  "annotation_quality": {
    "val_iaa_span_f1": null,
    "val_iaa_span_f1_ci95_low": null,
    "test_iaa_span_f1": null,
    "test_iaa_span_f1_ci95_low": null,
    "per_category_iaa": {},
    "unreliable_eval_categories": []
  },
  "known_limitations": [],
  "created_at": "..."
}
```

**`annotation_quality` é obrigatório**, com a seguinte especificação exata — nenhum
valor numérico solto é aceito como evidência sem estes parâmetros declarados junto:

- **Matching de span:** métrica primária = correspondência **exata** de offsets
  (`start`, `end`, `category` idênticos) entre as duas anotações independentes.
  Sobreposição (IoU ≥ 0.5) é uma métrica secundária/diagnóstica, reportada em separado,
  nunca substituindo a exata no gate.
- **Averaging:** F1 por categoria; uma categoria só entra no **macro**-F1 agregado se
  tiver suporte ≥ 5 spans na anotação de referência daquele split (mesmo piso do §5.4).
  Categorias abaixo do suporte mínimo são reportadas individualmente no manifest mas
  excluídas do macro agregado — evita que uma categoria com 1 exemplo domine ou seja
  ignorada de forma enganosa.
- **Intervalo de confiança:** bootstrap sobre **documentos** (não sobre spans
  individuais, para não quebrar o agrupamento), ≥ 1000 reamostragens, IC 95% publicado
  junto ao ponto estimado — obrigatório dado o tamanho pequeno do split (§5.4: ~30 docs).
- **Threshold normativo, fixado nesta RFC, não pelo release:** o piso mínimo é
  **macro-F1 ≥ 0.75 agregado e ≥ 0.5 por categoria treinável**, para `segmenter-real-v8.1`
  especificamente — não "recomendado", é o requisito desta release. Um release não pode
  declarar um piso menor para si mesmo; mudar o número exige alterar esta RFC (ou uma
  RFC sucessora), nunca só o manifest. **O gate compara o limite inferior do IC 95%
  contra o piso, não o ponto estimado** — um ponto de 0.76 com limite inferior de 0.60
  falha o gate.
- **Consequência por categoria:** uma categoria treinável cujo limite inferior de IC
  fique abaixo de 0.5 é marcada em `unreliable_eval_categories` — excluída de qualquer
  alegação de avaliação (val/test) até ser reanotada, ainda que continue elegível para
  treino (treino não depende de IAA, §9). Se a categoria marcada for uma das críticas do
  §16.2 (`dispositivo_abertura`, `resultado`, `acordao_decisorio_inicio`,
  `acordao_decisorio_fim`), a falha deixa de ser local e vira **erro rígido do release
  inteiro** (§12.1) — essas categorias são estruturais demais para isolar.
- **Consequência agregada:** IAA agregado abaixo de 0.75 (limite inferior do IC) é erro
  rígido, não-waivable (§12.1); bloqueia o release inteiro, `silver` ou `gold`.
- **Limite epistêmico explícito:** IAA mede **confiabilidade entre anotadores**, não
  **validade** contra a verdade-terreno — dois anotadores (ou famílias de LLM) podem
  concordar e ainda assim estarem sistematicamente errados por viés correlacionado. IAA
  alto é condição **necessária, não suficiente** para chamar um split de `gold`; a
  condição suficiente adicional é a validação contra referência humana do §9.1.

## 9. Política de anotação

### Dados de treino

Registros de treino exigem:

- uma anotação completa;
- validação mecânica;
- validação automática de consistência de pares;
- spot-review por amostragem de risco.

Registros de alto risco recebem revisão independente. Sinais de risco:

- spans propostos sobrepostos (extração heurística);
- pares de fronteira sem correspondência;
- rascunhos assistidos por modelo;
- decisões judiciais citadas (quoted);
- contagem de rótulos anormalmente alta;
- categorias raras;
- desacordo com extratores determinísticos.

### Dados de validação e teste

Cada documento de val/test exige:

- **duas anotações completas e independentes** (definição do §5.3);
- comparação de desacordos (gera o IAA do §8);
- adjudicação explícita;
- nenhum acesso a predições de modelo;
- nenhuma anotação baseada em rascunho de modelo anterior.

Uma anotação não é independente quando o revisor vê a primeira anotação ou uma predição
de modelo antes de produzir a sua.

### 9.1 Validação de anotadores-LLM contra referência humana (condição para `gold`)

Concordância entre duas execuções/famílias de LLM (§5.3) demonstra isolamento de
execução, não ausência de viés correlacionado — duas famílias, inclusive treinadas em
corpora sobrepostos, podem errar sistematicamente da mesma forma. Um split cuja única
evidência de qualidade é IAA entre anotadores-LLM é honestamente **`silver`**
(`llm-adjudicated`), não **`gold`**.

**Duas peças de evidência humana, deliberadamente separadas para evitar a dependência
circular entre qualificação do anotador, definição do split de teste e adjudicação:**

#### 9.1.1 Corpus de qualificação (calibração — reutilizável)

Um conjunto pequeno de documentos, **totalmente fora do ciclo de vida do §3.1**: nunca
passa por split-assignment (§10), nunca é candidato a train/val/test, e é retirado de
uma fonte/período explicitamente excluído de qualquer split (ex.: um lote de
documentos JURIS reservado só para isso, nunca alimentado ao extrator de candidatos do
pipeline principal). Cada documento tem rótulo final definido por um especialista
humano (jurista), sem qualquer anotação de LLM prévia.

Antes de uma configuração de anotador-LLM (modelo + versão de prompt/guideline) ser
aceita para produzir anotações de val/test, seu F1 de span exato contra o corpus de
qualificação deve atingir o piso do §8 (macro-F1 ≥ 0.75, limite inferior do IC). Como
este corpus **nunca é** o teste nem faz parte dele, ele pode ser reusado livremente
entre tentativas de configuração durante o desenvolvimento — iterar prompt/guideline
contra ele é calibração, não vazamento, porque nenhuma alegação final de desempenho do
*modelo segmentador* é feita sobre este corpus. A validação é repetida sempre que o
modelo, prompt ou guideline do anotador mudar de versão. Isso resolve a ordem de
dependência: qualificação → (só então) produção de anotações de val/test →
adjudicação → split-assignment (§10) — nunca o inverso.

#### 9.1.2 Auditoria cega do teste (verificação — uma única passagem)

Depois que o split de teste é montado pelo caminho normal (documentos anotados por
configurações já qualificadas em 9.1.1, adjudicados, split-assignment do §10), um
especialista humano realiza **uma única auditoria cega** sobre uma amostra do teste
já montado (mínimo 20% ou 10 documentos, o que for maior), sem acesso às anotações de
LLM daquele documento durante a auditoria.

Essa auditoria tem consequência estritamente limitada — **nunca retroalimenta a
configuração do anotador**:

- se o resultado da auditoria atinge o piso do §8, o release pode classificar aquele
  split como `gold`, registrando a amostra e o resultado no manifest;
- se não atinge, o release permanece `silver` — a consequência é uma reclassificação
  de nome, **não** um gatilho para ajustar prompt/guideline/modelo e reanotar. Reanotar
  em resposta ao resultado da auditoria transformaria a auditoria em tuning contra o
  teste, exatamente o padrão proibido pelo §3.3; se a qualidade for julgada insuficiente
  para uso, a via correta é aposentar aquele teste (§13.1) e formar um novo com uma
  configuração de anotador re-qualificada em 9.1.1 sobre documentos ainda não tocados.

**Enquanto o corpus de qualificação (9.1.1) não existir** (depende de disponibilidade de
revisão jurídica humana), releases nomeiam seus artefatos como `segmenter-silver-vN.M`,
não `segmenter-real-vN.M`, e o comando `build_gold_release` (§12) é um nome provisório —
renomear para `build_dataset_release` até então é aceitável e não exige nova RFC.

## 10. Política de splits

Atribuição de split acontece **somente após o documento atingir o estado mínimo
exigido pelo §9 para o papel que vai ocupar**: um documento só entra no manifest de
split como candidato a **treino** depois de anotado (uma anotação completa + validação
mecânica + resolução de spot-review de risco, §9); um documento só entra como candidato
a **validação ou teste** depois de adjudicado (duas anotações independentes + review,
§9). Nenhum documento entra em um manifest de split antes de atingir o estado exigido
para o papel correspondente — não existe uma regra única "após adjudicação" que se
aplique aos três splits por igual.

O splitter agrupa documentos relacionados de forma que um grupo não atravesse splits.
Chaves de agrupamento (quando disponíveis):

- número de processo normalizado;
- ID de processo da fonte;
- família de documentos;
- hash de conteúdo duplicado;
- cluster de quase-duplicatas;
- relação pai/derivado.

O construtor de splits rejeita:

- `document_id` repetido;
- hash de conteúdo normalizado repetido;
- pai e filho aumentado em splits diferentes;
- cluster de quase-duplicatas atravessando splits;
- registros derivados de documentos de val/test entrando no treino.

Alvo inicial:

```text
train: 70% | validation: 15% | test: 15%
```

Estratificado por tribunal e tipo de documento onde o suprimento permitir.
Enriquecimento de categorias raras em val/test é permitido, mas o release deve
descrever o conjunto resultante como **challenge/enriched set**, não como amostra
representativa de produção.

## 11. Validação mecânica

Todo registro em release satisfaz:

- schema JSON válido;
- `0 <= start < end <= len(text)`;
- nenhuma sobreposição proibida;
- categoria pertence à ontologia;
- contagens de pares start/end válidas;
- `_fim` não precede seu `_inicio`;
- `_fim` órfão é rejeitado;
- `_inicio` sem par exige razão explícita de allowed-unmatched;
- âncoras únicas duplicadas rejeitadas salvo permissão explícita;
- `text[start:end]` não vazio;
- todos os campos de proveniência exigidos pelo tipo de registro (documento/anotação/
  review) presentes.

A validação mecânica roda **in-process** (biblioteca), não via chamadas repetidas de
subprocesso a `opf_annotate.py`.

## 12. Comando de release

A operação chama-se:

```text
build_gold_release
```

*(Nome provisório — condicionado ao gate de referência humana do §9.1. Até esse gate
existir, o release resultante é nomeado `segmenter-silver-*`, não `segmenter-real-*`, e
`build_dataset_release` é um nome igualmente válido para o comando.)*

Ela **não promove candidatos** — empacota registros já anotados (treino, §9) ou
adjudicados (validação e teste, §9), com split-assignment já resolvido (§10):

1. carrega anotações (treino) e adjudicações (validação e teste);
2. verifica integridade de splits;
3. valida cada registro;
4. calcula contagens e hashes;
5. checa regras de prontidão configuradas independentemente;
6. escreve em diretório temporário;
7. verifica o release escrito;
8. renomeia atomicamente para o release ID final;
9. recusa sobrescrever release existente.

Cada item de `known_limitations` identifica exatamente uma regra consultiva/waivable
(§12.1) e uma razão — sem objeto formal de aprovação/expiração, que é ceremônia
desnecessária para uma equipe pequena. A revisão natural de um known limitation é o
próximo *major release* (§13.1), não uma data de expiração hardcoded:

```json
{
  "gate": "minimum_tribunal_count",
  "status": "known_limitation",
  "reason": "Release inicial é explicitamente TJRO-only"
}
```

### 12.1 Invariantes não-waivable

Waiver por regra individual não basta se **todas** as regras puderem ser waivadas — isso
é `--skip-gates` disfarçado de granularidade. Os gates do §14 dividem-se em duas classes
fixas, e a classe de cada gate (não só o resultado) é parte do contrato desta RFC:

- **Erros rígidos, nunca waivable, sempre bloqueiam o release:** schema de ontologia
  inválido; qualquer conflito de anotação não resolvido; vazamento entre splits (ID,
  hash exato, grupo ou quase-duplicata cruzando splits — §10); contaminação de teste
  (teste avaliado mais de uma vez, ou usado em seleção de checkpoint — §3.3/§13.1);
  checksums/integridade de release ausentes ou inválidos; IAA abaixo do piso agregado
  declarado (§8). `build_gold_release` recusa-se a produzir **qualquer** release,
  mesmo rotulado `silver`/experimental, se um destes falhar.
- **Consultivos/waivable — allowlist fechada, cada um registrado como
  `known_limitation` no formato acima:** diversidade de tribunal; diversidade de
  sistema-fonte; diversidade temporal; representatividade do conjunto de avaliação;
  revisão externa da anotação de teste — exatamente os itens já listados em §14 como
  "exigidos para alegações amplas de produção". Nenhum gate fora desta lista pode
  virar known limitation; adicionar um item à allowlist exige atualizar esta RFC, não
  um argumento de linha de comando.

Não existe `--skip-gates` genérico, e não existe caminho — por regra individual ou
composição de known limitations — para dispensar um erro rígido.

## 13. Treino baseline e avaliação de teste

O primeiro baseline usa: split de treino real anotado (§9); validação congelada; uma
arquitetura declarada; um comando de treino reprodutível; seeds fixas; hashes de
dependências e checkpoint; métricas de validação por época; **nenhuma avaliação de
teste por época**.

Seleção de checkpoint: métrica primária do §5.5 (macro-F1 de validação), com a regra
de desempate declarada. Diagnósticos secundários permitidos: span recall, F1 por
categoria, acurácia de fronteira, exact match por documento, val loss.

Avaliação de teste, após arquitetura + hiperparâmetros + checkpoint congelados:

1. calcular hash da configuração final;
2. registrar o resultado de validação selecionado;
3. destrancar o teste para **uma** avaliação;
4. avaliar exatamente uma vez;
5. publicar métricas agregadas e por categoria;
6. não continuar ajustando contra esse resultado.

Se o resultado de teste causar mudanças no modelo, aquele teste vira dado de
desenvolvimento e um novo teste trancado deve ser criado (foi exatamente o que
aconteceu com o teste v7 — §5.2).

### 13.1 Rotação do teste entre releases

"Avaliado uma vez" descreve o teste de **um** release; não implica que o mesmo teste
sirva para sempre. O ciclo completo:

- **Validação** — usada livremente durante o desenvolvimento para seleção de checkpoint
  e diagnóstico (§3.3), nunca reportada como número final de desempenho.
- **Teste de aceitação (holdout)** — um conjunto por *major release*
  (`segmenter-real-v8`, `v9`, ...), avaliado exatamente uma vez por essa versão maior.
  Uma vez usado, é consumido para fins de alegação final: releases *menores* do mesmo
  major (`v8.1`, `v8.2`, ...) reusam o mesmo treino/validação mas **não reavaliam o
  mesmo holdout como medição nova** — uma reavaliação do mesmo holdout só é reportada
  como diagnóstico de regressão (comparação), nunca como nova estimativa de desempenho.
- Um novo holdout major é sorteado de documentos nunca antes tocados sob dois gatilhos
  independentes, ambos registrados no manifest do novo release:
  1. **reação a teste** — uma mudança de modelo motivada pelo resultado do teste
     (regra "não continuar ajustando" acima) aposenta o teste consumido
     (`retired_test_release`) e sorteia um substituto;
  2. **novo candidato a model release** — uma configuração distinta da que já
     consumiu um holdout (ex.: o vencedor de validação da matriz de ablação sintética
     do PR 4/§15, se e quando for proposto para substituir o baseline em produção)
     recebe seu **próprio holdout**, sorteado no momento em que aquele candidato é
     declarado pronto para uma avaliação de aceitação — nunca reaproveitando um
     holdout que outra campanha já consumiu (`new_candidate_release`). Este gatilho é
     independente do primeiro: nem toda proposta de novo candidato implica que o
     teste anterior "causou uma mudança".
- Se diagnóstico repetido contra o mesmo teste for genuinamente necessário entre majors
  (ex.: checar regressão antes de um release menor), isso só pode ocorrer contra um
  **dev-test/benchmark set separado**, explicitamente marcado como reutilizável, com
  cada consulta registrada (contador de usos + data) no manifest — nunca contra o
  holdout de aceitação.
- **Durante** a busca de ablação do PR 4/§15 (matriz A/B/C/D), nenhum holdout de
  aceitação é tocado — a seleção entre configurações usa exclusivamente validação
  (§3.3). O holdout do baseline real (PR 3/§15) permanece consumido e não é reavaliado
  para o vencedor sintético; se esse vencedor for proposto para produção, ele segue o
  gatilho 2 acima e recebe holdout próprio antes de qualquer alegação de model release
  (§16.2).

### 13.2 Mecanismo real de trancamento

Um `test.jsonl` versionado em texto claro no repositório público não está trancado —
qualquer sessão de desenvolvimento pode lê-lo a qualquer momento. O trancamento é
implementado assim:

- No momento do split-assignment (§10), o conteúdo do split de teste é cifrado (ex.:
  `age`/`gpg` com chave mantida fora do repositório) ou publicado apenas como blob
  privado (ex.: item privado no Internet Archive — não o item público usado para os
  dados-fonte). O repositório versiona somente o **hash sha256** do teste em claro, no
  manifest de split, nunca o conteúdo.
- O "destrancamento" do passo 3 acima é uma operação nomeada e registrada: busca/decifra
  o conteúdo, executa a avaliação exatamente uma vez, e grava no manifest do release o
  timestamp, o executor e o hash do resultado — nunca uma leitura ad hoc do arquivo por
  um desenvolvedor.
- Depois de consumido (§13.1), o conteúdo em claro pode ser versionado no repositório
  para fins de auditoria (o segredo já não protege nada), mas somente **após** o
  registro de consumo já existir no manifest — nunca antes.

Aprendizados mecânicos do PR #832 que **permanecem válidos** para o runner: processo
por época com resume via `--checkpoint` (o trainer do `opf` vaza RAM em processo
longo), e os hiperparâmetros do sweep (lr 5e-5, batch 1, grad-accum 4) como ponto de
partida — não como configuração congelada.

## 14. Gates de prontidão

Cada gate tem resultado independente e pertence a exatamente uma das duas classes do
§12.1 (rígido/não-waivable ou consultivo/waivable).

**Exigidos para treino baseline (todos rígidos, §12.1):**

- schema de ontologia válido;
- train/val/test disjuntos por grupo, ID e hash exato;
- nenhum conflito de anotação não resolvido;
- todo registro de val/test com duas anotações independentes + adjudicação;
- IAA de val/test computado, publicado no manifest **e** acima do piso agregado
  declarado (§8) — abaixo do piso é falha rígida, não apenas ausência de número;
- suporte mínimo de treino por categoria (§5.4);
- suporte mínimo de validação para métricas reportadas;
- checksums de release gerados;
- release construído em CI a partir de um commit identificado, com dependências
  pinadas (`dependency_lock_hash` do §8 registrado) — "working tree limpa" não é a
  garantia real; um build local sem CI não estabelece reprodutibilidade, mesmo com
  árvore limpa;
- SHA Git completo registrado.

**Exigidos para alegações amplas de produção:**

- múltiplos tribunais;
- múltiplos sistemas-fonte;
- diversidade temporal;
- conjunto de avaliação representativo;
- anotação de teste externa ou revisada independentemente.

Um modelo TJRO-only **pode** ser lançado, mas nomeado e descrito como TJRO-específico.

## 15. Plano de implementação

Três entregas — não cinco — antes do primeiro número confiável; sintético continua
como uma quarta entrega, subordinada e posterior.

**PR 1 — Contrato de artefatos, splitter e release imutável.** Schemas de registro
(`documents/`, `annotations/`, `reviews/`); IDs determinísticos e hashes de conteúdo;
validação de pares; checagens cross-split por ID/hash; clustering de duplicatas;
splitter determinístico por grupo com a política de elegibilidade do §10; testes de
vazamento e rótulos malformados; `build_gold_release`/`build_dataset_release`; gates
rígidos e known limitations independentes (§12.1); saída atômica em
`dataset-releases/<release-id>/`; manifest completo (incl. IAA, §8); checksums;
verificação de build reprodutível em CI a partir de commit + deps pinadas (§14).
Reaproveita `transform.py`, `dedup.py`, `split_guard.py`, `validators.py`,
`provenance.py` do PR #832 (com os fixes da review — ver §18). Sem treino, sem
sintético.

**PR 2 — Corpus real anotado/adjudicado + dataset card.** Ingestão dos ativos do
PR #832 conforme o mapa de disposição do §18; corpus de qualificação de anotador-LLM
(§9.1.1); qualificação de cada configuração de anotador antes de produzir anotações
de val/test; anotação do treino e adjudicação de validação/teste até as metas do §5.4;
auditoria cega do teste (§9.1.2); primeiro `segmenter-silver-v8.1` (ou `-real-` se o
gate de §9.1 passar) publicado via PR 1; **dataset card** publicado junto ao release —
resumo legível por humano do manifest: escopo (tribunal/fonte/período), IAA agregado e
por categoria, known limitations, uso pretendido e não-pretendido.

**PR 3 — Trainer do baseline real + model card.** Um runner de treino; seleção de
checkpoint só por validação (§13); manifest de experimento; avaliação de teste única e
trancada, consumindo o holdout de `segmenter-real-v8.1` sob o gatilho "reação a teste"
do §13.1; comparação com baseline trivial, IC bootstrap e pisos por categoria crítica
(§16.2); **model card** publicado junto ao checkpoint.

**PR 4 — Experimentação sintética (RFC 0011 revisada).** Só após PRs 1–3 produzirem um
baseline confiável. Critérios de entrada: declarar versão do gerador, famílias de
template, seeds, origem dos phrase banks, distribuição de classes, razão
real/sintético, release exato de dados reais usado, protocolo de seleção
validation-only. Matriz mínima de experimentos:

```text
A: só real
B: real + sintético estrutural
C: real + real aumentado
D: real + sintético estrutural + real aumentado
```

Sintético é aceito como útil apenas se melhorar a métrica de validação pré-declarada
sem degradar materialmente categorias críticas. O holdout de `segmenter-real-v8.1`
permanece trancado durante toda a busca de ablação (seleção é só por validação, §13.1);
se um vencedor sintético for proposto para substituir o baseline em produção, ele segue
o gatilho "novo candidato a model release" do §13.1 e recebe holdout próprio antes de
qualquer alegação de model release — nunca reaproveita o holdout já consumido pelo
PR 3.

## 16. Critérios de aceitação do primeiro release

Aceitar o **dataset** (linhagem íntegra, procedimento correto) não implica aceitar o
**modelo** para uso — são critérios distintos, versionados separadamente (§16.2).

### 16.1 Aceitação do dataset release

O dataset release está completo quando:

- todo registro de val/test tem duas anotações independentes e um registro de
  adjudicação;
- nenhum grupo de documentos, duplicata exata ou quase-duplicata conhecida atravessa
  splits;
- todo rótulo passa nas regras semânticas de par e na validação mecânica;
- um release é imutável e reprodutível a partir de um build de CI sobre commit + deps
  pinadas (§14) — não meramente "árvore local limpa";
- IAA de val/test atinge o piso declarado (§8), com os erros rígidos do §12.1 todos
  limpos;
- toda alegação publicada declara escopo de tribunal e fonte, e usa `silver`/`gold`
  conforme o gate do §9.1;
- nenhum registro sintético é necessário para o primeiro baseline confiável;
- outro desenvolvedor consegue reproduzir o release apenas com as instruções do
  repositório.

### 16.2 Aceitação do model release (deploy) — critério de utilidade mínima

Um checkpoint totalmente reprodutível com macro-F1 de teste próximo de zero satisfaz
todos os critérios do §16.1 e ainda assim não serve a nenhum propósito — "confiável"
nesta RFC significa **auditável**, não **adequado ao uso**. Um model release exige
adicionalmente:

- **Baseline trivial declarado**: comparação, no mesmo teste trancado, contra um
  extrator heurístico/determinístico já existente (ex.: os extratores de fronteira do
  PR 2/§18) ou, na ausência de um, contra predição por classe majoritária. O modelo deve
  superar esse baseline por uma margem pré-declarada (recomendado: ≥ 0.10 de macro-F1)
  para ser elegível a deploy;
- **Intervalo de confiança no resultado de teste**: bootstrap sobre documentos (mesma
  metodologia do §8), obrigatório dado o tamanho pequeno do teste (§5.4). Um F1 pontual
  sem IC não é uma alegação aceitável de desempenho;
- **Pisos pré-declarados por categoria operacionalmente crítica** (mínimo:
  `dispositivo_abertura`, `resultado`, `acordao_decisorio_inicio`,
  `acordao_decisorio_fim`), declarados antes da avaliação de teste (§13) junto com o
  hash de configuração. Falhar um piso crítico bloqueia o deploy mesmo com macro-F1
  agregado aceitável — não há trade-off implícito entre categorias críticas e não;
- essas evidências (baseline trivial, IC, pisos por categoria) compõem o **model card**
  publicado junto ao checkpoint, distinto do manifest de dataset.

O checkpoint é selecionado só por macro-F1 de validação (§13) e o teste é avaliado uma
vez, após congelamento da configuração (§13/§13.1). `release_id` de dataset e de model
release são versionados separadamente (`segmenter-real-v8.1` para o dataset,
`segmenter-model-v8.1` para o checkpoint que o usa), permitindo que um dataset seja
aceito enquanto um modelo treinado sobre ele ainda não atinge a barra de utilidade.

## 17. Métrica de sucesso

O primeiro sucesso não é o F1 mais alto possível. É um resultado cuja linhagem,
qualidade de anotação, integridade de splits e procedimento de avaliação são fortes o
suficiente para que o F1 reportado signifique o que aparenta significar.

## 18. Disposição dos ativos do PR #832

| Ativo do PR #832 | Destino nesta RFC | Disposição |
|---|---|---|
| `transform.py`, `dedup.py`, `split_guard.py`, `validators.py`, `provenance.py` + testes | PR 1 | Reaproveitar com os fixes da review — é o melhor código do PR |
| Extratores JURIS (`juris_extract_gold_candidates.py`, internal-search, preliminar, âncoras únicas) | PR 2 (construção do corpus) | Reaproveitar como estão: a saída deles **é** o registro de documento (§8) |
| 131 docs das rodadas A–F | `documents/` + `annotations/` | Rebaixar: docs de anotação única viram *anotados* (elegíveis a treino); docs assistidos por modelo são treino-only, permanentemente inelegíveis para val/test |
| Seed original de 20 docs (val/test com ensemble) | Mais próximo de *adjudicado* | Re-expressar a verificação ensemble como registros de review; utilizável como validação, **nunca** como teste (§5.2) |
| Stack sintético (`renderer`, `phrase_banks`, `hybrid`, `llm_content`, `llm_judge`, `diagnostics`, `compose_mix`) | PR 4 apenas | Estacionar sem merge ou mergear atrás de fronteira "experimental"; os phrase banks têm valor independente (codificam achados do corpus real) |
| Aprendizados do runner Kaggle (processo-por-época, hiperparâmetros) | PR 3 | Manter a mecânica; descartar o checkpoint selecionado e o número 0.567 |
| RFC 0011 (PR #831) | PR 4 | Sobrevive como design doc da camada experimental, subordinada a esta RFC |
