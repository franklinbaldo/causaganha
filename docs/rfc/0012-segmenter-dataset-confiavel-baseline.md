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

**Exceção estreita, deliberadamente delimitada (§9.2): aumento sintético de âncoras.**
A razão de fundo para gatear dados sintéticos atrás de um baseline real congelado é que
sem nenhum sinal de avaliação confiável não há como saber se uma mudança na composição
do treino ajudou ou atrapalhou — não é burocracia de processo, é a impossibilidade
prática de medir o efeito. Essa razão não se aplica por igual a toda forma de dado
sintético: gerar variações curtas de uma âncora já observada em exemplos reais (frases
de 1–5 palavras, nunca um documento inteiro — a mesma granularidade de categoria do
§11) é um risco qualitativamente menor do que sintetizar um acórdão inteiro. Por isso
esta categoria estreita — só variação de frase-âncora, nunca geração de documento
inteiro nem híbrido real/sintético — é permitida **antes** do baseline real, sujeita às
três salvaguardas do §9.2, no lugar do gate de ablação completo do §15/PR 4. Toda outra
forma de dado sintético (documentos sintéticos inteiros, híbridos, `sintético
estrutural` do §18) permanece sob a regra geral acima — adiada para depois do baseline
real, via o processo A/B/C/D do §15.

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
   - **adicionar categoria** (minor): anotações existentes continuam válidas **como
     anotações**, mas adicionar uma categoria **não é retrocompatível para supervisão de
     treino**: em token/span classification, ausência de span é lida pelo treinador como
     exemplo negativo (`O`), não como "categoria ainda não revisada" — tratar documentos
     antigos como negativos para a categoria nova introduziria falso-negativo sistemático.
     Por isso toda anotação declara `covered_categories` (§8): o subconjunto da ontologia
     que o anotador efetivamente considerou. Um documento só entra na loss/no suporte de
     uma categoria C se C ∈ `covered_categories` da anotação usada; documentos cuja
     anotação antecede a introdução de C ficam **mascarados** para C (nem positivo nem
     negativo) até um passe de revisão dirigido (checar especificamente a presença de C,
     não uma reanotação completa) atualizar `covered_categories`;
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
6. **Piso mínimo de utilidade do model release, fixado nesta RFC para `v8.1` — não
   deixado para o release declarar (§16.2 aplica esta regra, não a define de novo):**
   - **Contra o baseline trivial:** regra objetiva, não uma margem arbitrária —
     bootstrap sobre documentos da **diferença** (F1 do modelo − F1 do baseline
     heurístico/majoritário) no teste trancado, ≥ 1000 reamostragens; elegível a
     deploy apenas se o **limite inferior do IC 95% da diferença for > 0** (melhora
     estatisticamente detectável, não um número que o release escolhe);
   - **Pisos por categoria operacionalmente crítica** (`dispositivo_abertura`,
     `resultado`, `acordao_decisorio_inicio`, `acordao_decisorio_fim`): macro-F1 do
     **ponto estimado** ≥ 0.5 no teste trancado (ponto, não limite inferior — o
     suporte dessas categorias em ~30 documentos de teste é baixo demais para um IC
     discriminar, mesma lógica do §8). Mudar este piso exige alterar esta RFC.
7. **Nem toda categoria single-anchor é limitada a uma ocorrência por documento —
   a razão de ser da categoria decide.** O piso mecânico padrão do §11 (`validate_
   single_anchor_duplicates`) rejeita mais de uma ocorrência por documento salvo
   permissão explícita. Isso é correto para categorias cujo valor é um fato sobre
   a decisão **como um todo**: `dispositivo_abertura` e `resultado` porque só a
   menção **operativa** conta (não toda menção em prosa de fundamentação);
   `ref_processual` porque sua função é *record-linking* — ligar este texto a
   exatamente um processo, e um vínculo multivalorado não serve a esse propósito
   (referências a **outros** processos citados na fundamentação — precedente,
   condenação anterior — ficam deliberadamente sem tag, não é omissão).
   `fundamentacao_legal` e `valor_condenacao` são o oposto: uma decisão real cita
   a lei mais de uma vez para pontos diferentes, e pode declarar mais de um valor
   genuinamente distinto (dano moral e dano material, ou um valor original e um
   corrigido). Deduplicar essas duas para "primeira ocorrência" — o que os dois
   scripts de ingestão faziam antes deste achado (piloto/lote 1, ver §9) —
   descarta sinal real silenciosamente. `ontology.ALLOW_MULTIPLE_SINGLE_ANCHOR`
   nomeia as categorias isentas do piso de ocorrência única; toda chamada a
   `mechanical.validate_record` no pipeline (gate de release, os dois scripts de
   ingestão) passa esse conjunto — decidir isso independentemente em cada
   call site é como a política diverge.

## 6. Não-objetivos do primeiro release

Explicitamente adiados (viram Fase 5+, sob a RFC 0011 revisada). "Geração de documentos
sintéticos" aqui significa **documento inteiro** — a exceção estreita do §3.4/§9.2
(variação de frase-âncora curta, seedada em spans reais, nunca um documento completo)
não é adiada; é permitida agora sob as três salvaguardas do §9.2:

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

Artefato canônico de documento/anotação/review é **XML com tags inline** — um arquivo
por registro, não uma tabela — onde cada rótulo é um elemento XML real que envolve o
próprio trecho do span, em vez de um triplo separado `{categoria, start, end}` apontando
para um intervalo de offset. `start`/`end` nunca são armazenados; são recalculados
percorrendo a árvore já parseada e contando um offset de caractere corrente. Isso torna
uma classe inteira de bug estruturalmente impossível — desvio de offset por uma edição
que toca o texto mas não os rótulos — já que a posição *é* o próprio posicionamento da
tag, e torna um registro trivialmente auditável por humano (abrir o arquivo, ler o
documento já marcado).
**Categorias start/end pair usam aninhamento XML de verdade, não convenção de nome.**
Um par plano `<relatorio_inicio>`/`<relatorio_fim>` são dois nomes de tag sem relação
estrutural que só coincidem no prefixo; XML já tem uma forma nativa de dizer "estas duas
coisas delimitam uma região" — aninhamento. Um par casado renderiza como um wrapper
`<relatorio>` nomeado pela categoria-base, com filhos genéricos `<inicio>`/`<fim>`
reaproveitados por toda categoria pair (nunca codificados no nome da tag); um par sem
fechamento ainda ganha o wrapper, só que com um único filho. Qualquer outra coisa que
caia dentro da região — a âncora de outra categoria, como `ref_processual` dentro do
`cabecalho` de um documento — vira filho aninhado também, encontrado por contenção de
intervalo genérica, sem conhecimento hardcoded de qual categoria pode conter qual.
Categoria single-anchor (sem par `_inicio`/`_fim`) continua uma tag folha plana, como
antes — não há região a expressar. As strings de categoria treináveis (`Label.category`,
ex. `"relatorio_inicio"`) não mudam — isso é uma questão de serialização, não de
taxonomia.

**Nem todo par aninha.** RFC 0012 §11 só proíbe *rótulos* sobrepostos (âncoras curtas);
nunca checou se duas *regiões* (do próprio inicio ao próprio fim de uma categoria)
sobrepõem parcialmente uma à outra — e empiricamente, 3 de 150 documentos reais têm
exatamente isso (uma cláusula `custas`/`honorarios` entrelaçada, ou `voto`/`ementa`
cruzando). XML não representa sobreposição parcial como aninhamento, então qualquer par
de regiões que sobreponha parcialmente é rebaixado de volta a tags folha planas e sem
wrapper (`<relatorio_inicio>`/`<relatorio_fim>`) — o mesmo formato usado em toda parte
antes desta revisão, agora restrito ao caso raro que precisa dele.

**Tags inline são a técnica de produção recomendada para a Técnica 1 — anotação
assistida por LLM sobre documento real (§9)** —, não só o formato de armazenamento. (A
Técnica 2, aumento sintético de âncoras, é um mecanismo diferente, com sua própria seção
e salvaguardas: §9.2.) Aritmética de posição (`start`/`end` como inteiros) é um modo de
falha conhecido de LLMs — contagem de caracteres não se alinha com tokenização e degrada em
textos longos — enquanto reescrever o documento inserindo tags é uma tarefa de
texto-para-texto, o tipo de tarefa em que um LLM é confiável. Um anotador-LLM produz o
documento inteiro com tags inseridas; offsets nunca são pedidos ao modelo, apenas
derivados depois, mecanicamente, da árvore já parseada — a mesma técnica usada para
`document_id`/`annotation_id` (nunca confiar num valor que o modelo poderia calcular
errado quando o dado necessário já está disponível para derivação determinística). Isso
não elimina a necessidade de verificação: qualquer ferramenta de ingestão que aceite texto
marcado produzido por um LLM (ou por qualquer processo que não seja a própria store
reescrevendo a partir de `document.text` já validado) **deve** comparar o texto
desmarcado, byte a byte, contra o `document.text` de referência do documento antes de
aceitar o resultado — uma divergência (uma palavra omitida, um espaço normalizado, um erro
de digitação "corrigido") é rejeição mecânica imediata, nunca correção silenciosa nem
aproximação aceita. Esse é um requisito de processo, não algo que o schema por si só possa
verificar depois — uma vez reduzido a `labels: list[Label]`, o registro armazenado não
retém o suficiente para reconstruir essa checagem; ela só é possível no momento da
ingestão, com o texto candidato ainda em mãos.

Um documento vive em `documents/<document_id>.xml`; à medida que trabalho é feito sobre
ele, também ganha arquivos de anotação e depois de review, sem que seu arquivo original
seja alterado ou removido (§3.1). Cada anotação/review carrega sua própria cópia
integralmente marcada do texto do documento (decisão da RFC 0012 PR 2: apenas uma
anotação canônica por arquivo, então não há ambiguidade a desduplicar). `dataset-releases/
<release-id>/` não contém cópias de documentos "promovidos"; contém manifests que
referenciam `document_id`s por hash:

```text
data/segmenter/
  documents/<document_id>.xml
  annotations/<document_id>/<annotation_id>.xml
  reviews/<document_id>/<review_id>.xml
  dataset-releases/
    <release-id>/
      split_manifest.csv           # split-assignment desta build (§10) — não um
                                    # estado do documento, um artefato da build
      manifest.csv                 # manifest final imutável, só existe após
                                    # build_gold_release (§12)
```

Os artefatos de nível release (`manifest.csv`, `split_manifest.csv`) permanecem CSV
canônico, não XML — são metadados agregados puros, sem texto-com-spans para marcar; ver
a seção "Manifest de release de dataset" abaixo.

### Registro de documento

`documents/<document_id>.xml`: atributo `id` na raiz (`document_id`); elementos
`<source system="..." tribunal="..." document_type="..." uri="..." hash="..."/>`,
`<extraction method="..." version="..."/>`, `<grouping normalized_process_number="..."
source_process_id="..." document_family="..." parent_document_id="..."/>` (atributos
omitidos quando `None`); e `<text>...</text>` — o texto puro do documento, com
`proposed_labels` marcados inline quando existirem.

### Registro de anotação

`annotations/<document_id>/<annotation_id>.xml`: atributos `id` (o `annotation_id`,
`sha256(document_id + annotator_id + completed_at + labels + ...)`) e `document_id` na
raiz; `<annotator id="..." model_family="..." guideline_version="..."
seeded_with="..."/>`; `<ontology_version>`; `<covered_categories>` (lista de
`<category>`); `<allowed_unmatched>` (lista de `<entry base="..." reason="..."/>`);
`<completed_at>`; `<annotation_method>`; e `<text>...</text>` — cópia do texto do
documento com `labels` marcados inline.

`annotation_id` é determinístico (hash do conteúdo), não um contador — duas anotações
com o mesmo conteúdo produzem o mesmo ID; qualquer diferença de rótulo, anotador ou
timestamp produz um ID novo, nunca sobrescrevendo o anterior (§3.1). `covered_categories`
é o subconjunto da ontologia que este anotador considerou (ver §5.1 para a regra de
mascaramento de categorias fora desse conjunto). `seeded_with` só admite `"none"` para
anotações que contam como independentes (§5.3). A ordem original de `labels` na lista
(semanticamente significativa para o hash do ID e para igualdade do registro) é
preservada por um atributo `ord` em cada elemento de rótulo, independente de sua posição
física no arquivo (que segue a ordem do documento, para o texto fluir linearmente).

### Registro de review (adjudicação)

`reviews/<document_id>/<review_id>.xml`: atributos `id` (o `review_id`,
`sha256(document_id + input_annotation_ids + approved_at + ...)`) e `document_id` na
raiz; `<input_annotations>` (lista de `<annotation_id>`); `<status>`;
`<allowed_unmatched>`; `<reviewers>` (lista de `<reviewer>`); `<resolution>`; `<notes>`
(lista de `<note>`); `<approved_at>`; e `<text>...</text>` — cópia do texto do documento
com `final_labels` marcados inline.

`input_annotations` referencia explicitamente **quais** registros de anotação foram
resolvidos — não apenas o `document_id` (um documento pode ter mais de duas anotações
ao longo do tempo; o review precisa dizer qual par ele adjudicou).

### Manifest de release de dataset

Uma tabela `manifest.csv` discriminada por `record_kind`: uma linha `"manifest"` com
os campos escalares (`release_id`, `ontology_version`, `guideline_version`,
`source_commit`, `dependency_lock_hash`, `ci_provider`, `ci_run_id`,
`split_manifest_hash`, `iaa_seed`, `iaa_resamples`, `created_at`, mais as quatro
colunas escalares de `annotation_quality` — `val_iaa_span_f1`,
`val_iaa_span_f1_ci95_low`, `test_iaa_span_f1`, `test_iaa_span_f1_ci95_low`), e uma
linha por elemento para cada campo um-para-muitos: `"split_hash"` (`role`, `value`),
`"document_resolution"` (`role`, `key`=`document_id`, `value`=`resolution_id`),
`"count"` (`role`, `value`), `"tribunal"` (`key`, `value`), `"document_type"` (`key`,
`value`), `"per_category_iaa"` (`key`, `value`), `"unreliable_category"` (`ordinal`,
`key`), e `"known_limitation"` (`key`=`gate`, `value`=`status`, `extra`=`reason`).

**`document_resolutions` é obrigatório**: pina o `annotation_id` (treino) ou
`review_id` (validação/teste) exato usado para cada documento nesta build. Sem isso,
reconstruir um release a partir do mesmo conjunto de `document_id`s poderia
silenciosamente pegar anotações diferentes se o documento tiver sido reanotado entre
duas builds — `document_resolutions` é o que torna a build determinística, não apenas
a lista de IDs.

**`annotation_quality` é obrigatório**, com a seguinte especificação exata — nenhum
valor numérico solto é aceito como evidência sem estes parâmetros declarados junto:

- **Matching de span:** métrica primária = correspondência **exata** de offsets
  (`start`, `end`, `category` idênticos) entre as duas anotações independentes.
  Sobreposição (IoU ≥ 0.5) é uma métrica secundária/diagnóstica, reportada em separado,
  nunca substituindo a exata no gate.
- **Averaging:** F1 por categoria; uma categoria só entra na agregação (macro-F1 e no
  gate agregado) se tiver suporte ≥ 5 spans na anotação de referência daquele split
  (mesmo piso do §5.4). Categorias abaixo do suporte mínimo são reportadas
  individualmente no manifest mas excluídas do macro agregado — evita que uma
  categoria com 1 exemplo domine ou seja ignorada de forma enganosa.
- **Intervalo de confiança:** bootstrap sobre **documentos** (não sobre spans
  individuais, para não quebrar o agrupamento), ≥ 1000 reamostragens, IC 95% publicado
  junto ao ponto estimado — obrigatório dado o tamanho pequeno do split (§5.4: ~30 docs).
- **Threshold normativo, fixado nesta RFC, não pelo release:** o piso mínimo é
  **macro-F1 ≥ 0.75 agregado e ≥ 0.5 por categoria treinável**, para `segmenter-real-v8.1`
  especificamente — não "recomendado", é o requisito desta release. Um release não pode
  declarar um piso menor para si mesmo; mudar o número exige alterar esta RFC (ou uma
  RFC sucessora), nunca só o manifest.
- **Estatística do gate agregado:** compara o **limite inferior do IC 95%** contra o
  piso — um ponto de 0.76 com limite inferior de 0.60 falha o gate. Com ~30 documentos
  no split inteiro, este IC tem suporte suficiente para ser informativo.
- **Estatística do gate por categoria (suporte importa):** a ~5 spans (o piso mínimo de
  suporte), um IC bootstrap por categoria é largo demais para um gate por limite
  inferior ser estatisticamente viável — exigiria concordância quase perfeita e
  produziria falsos-negativos do próprio gate. Por isso o piso de 0.5 por categoria é
  avaliado de dois jeitos, dependendo do suporte disponível naquele split:
  - **suporte ≥ 15 spans:** gate pelo **limite inferior do IC 95%** ≥ 0.5, igual ao
    agregado;
  - **suporte entre 5 e 14 spans:** gate pelo **ponto estimado** ≥ 0.5 (o IC é
    publicado como evidência de incerteza no manifest, não usado para o pass/fail);
    a categoria é adicionalmente marcada `insufficient_power_for_ci_gate` para deixar
    claro que a barra estatística é mais fraca aqui.
  Este limiar de 15 spans é declarado nesta RFC, não escolhido pelo release.
- **Consequência por categoria:** uma categoria treinável que falha seu gate (pela
  regra de suporte acima) é marcada em `unreliable_eval_categories` — excluída de
  qualquer alegação de avaliação (val/test) até ser reanotada, ainda que continue
  elegível para treino (treino não depende de IAA, §9). Se a categoria marcada for uma
  das críticas do §5.6/§16.2 (`dispositivo_abertura`, `resultado`,
  `acordao_decisorio_inicio`, `acordao_decisorio_fim`), a falha deixa de ser local e
  vira **erro rígido do release inteiro** (§12.1) — essas categorias são estruturais
  demais para isolar.
- **Consequência agregada:** IAA agregado abaixo de 0.75 (limite inferior do IC) é erro
  rígido, não-waivable (§12.1); bloqueia o release inteiro, `silver` ou `gold`.
- **Limite epistêmico explícito:** IAA mede **confiabilidade entre anotadores**, não
  **validade** contra a verdade-terreno — dois anotadores (ou famílias de LLM) podem
  concordar e ainda assim estarem sistematicamente errados por viés correlacionado. IAA
  alto é condição **necessária, não suficiente** para chamar um split de `gold`; a
  condição suficiente adicional é a validação contra referência humana do §9.1.

## 9. Política de anotação

Antes de comprometer um lote inteiro a uma guideline nova ou revisada, um piloto de
**um único documento** é produzido e escrutinado manualmente (além da validação
mecânica do §11): a anotação resultante é comparada contra a instrução, contra
qualquer anotação existente do mesmo documento (se houver) e contra o texto-fonte,
em busca de lacunas de instrução — ambiguidade que levaria dois anotadores a decisões
diferentes, categoria mal especificada, exemplo insuficiente na guideline — antes que
o mesmo defeito se propague para um lote inteiro. O piloto separa dois tipos de
achado, tratados de forma diferente:

- **Lacuna de instrução** (a guideline permite mais de uma leitura razoável): dispara
  revisão da guideline (bump de `guideline_version`, ponto 1 do §5 — não invalida
  anotações existentes) e um **segundo piloto sobre o mesmo documento**, para checar
  se a revisão de fato converge a decisão antes de liberar o lote sob a nova versão.
- **Defeito do corpus-fonte** (ex.: um lote de origem sistematicamente sub-anotado
  numa categoria): não é motivo para alterar a guideline — vira uma nota de risco
  desse lote específico, monitorada no spot-review de risco ("Dados de treino",
  abaixo), não um problema geral do processo de anotação.

**Prompt canônico da Técnica 1.** `data/segmenter_splits/technique1_annotation_prompt.md`
é o prompt a usar, verbatim, ao acionar um subagente por documento para anotação real
(Técnica 1). Improvisar esse prompt por chamada foi a causa provável da taxa de falha de
~45% do primeiro lote real (8 de 20 subagentes produziram zero tags apesar de instrução
explícita — o próprio arquivo do prompt documenta o diagnóstico via transcript, seção
"Why it's shaped this way"). O template existe para que resultados sejam comparáveis
entre documentos e sessões, e para que ajustes de prompt aconteçam num lugar só em vez
de reinventados ad hoc a cada lote.

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
- desacordo com extratores determinísticos;
- **reconstrução verbatim diverge do `document.text` já armazenado** (achado do
  segundo piloto de anotação: um anotador-LLM pode duplicar um trecho em vez de
  envolvê-lo in-place ao inserir uma tag — XML sintaticamente válido, mas não mais
  uma reconstrução fiel do documento). Isto **não é rejeição automática** — é sinal
  de risco como os demais desta lista: escalona o registro para revisão
  independente, que decide se conserta (reprocessar a anotação) ou descarta. Nunca
  bloqueia sozinho o pipeline de produção nem o release (§11 não trata isto como
  invariante rígido).

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

#### 9.1.1 Corpus de qualificação: calibração vs. aceitação (evita otimismo por reuso)

Um conjunto pequeno de documentos, **totalmente fora do ciclo de vida do §3.1**: nunca
passa por split-assignment (§10), nunca é candidato a train/val/test, e é retirado de
uma fonte/período explicitamente excluído de qualquer split (ex.: um lote de
documentos JURIS reservado só para isso, nunca alimentado ao extrator de candidatos do
pipeline principal). Cada documento tem rótulo final definido por um especialista
humano (jurista), sem qualquer anotação de LLM prévia.

Medir o gate de aceite no **mesmo** conjunto usado para iterar prompt/guideline produz
uma estimativa otimista — overfitting do anotador ao corpus de calibração, ainda que
não seja vazamento do segmentador em si. Por isso o corpus se divide em duas partes
fixas, disjuntas e de tamanho declarado **antes** de qualquer iteração:

- **`annotator-calibration-dev`** (tamanho declarado: 30 documentos; suporte mínimo
  declarado: ≥ 10 spans por categoria treinável) — reutilizável livremente durante o
  desenvolvimento de uma configuração de anotador; iterar prompt/guideline contra ele
  é a calibração pretendida, não um vazamento.
- **`annotator-acceptance-holdout`** (tamanho declarado: 20 documentos; suporte
  mínimo declarado: ≥ 10 spans por categoria treinável; disjunto do calibration-dev,
  mesma fonte/período excluído de qualquer split de §10) — tocado para medir o gate de
  aceite **uma única vez por versão de configuração** (hash de modelo + prompt +
  guideline); uma nova versão exige nova avaliação, sempre contra este **mesmo**
  holdout fixo, nunca um recém-sorteado — do contrário a comparação entre versões
  perde validade. Reavaliações repetidas do mesmo holdout ao longo de muitas versões
  são contadas no manifest; acima de 20 reavaliações o holdout é aposentado e
  substituído por um novo, mesma disciplina de desgaste do §13.1.

O gate de aceite (§8: macro-F1 ≥ 0.75 agregado, limite inferior do IC) é medido
**apenas** no `annotator-acceptance-holdout`, nunca no `calibration-dev`. Isso resolve a
ordem de dependência: calibração (livre) → aceite (uma vez por versão, no holdout) →
produção de anotações de val/test → adjudicação → split-assignment (§10) — nunca o
inverso.

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

### 9.2 Técnica 2 — Aumento sintético de âncoras (train-only)

Duas técnicas de LLM distintas, deliberadamente nomeadas para não serem confundidas:

- **Técnica 1 — anotação assistida por LLM** (§8, §9, §9.1): o LLM opera **sobre um
  documento real já existente em `documents/`**, reescrevendo-o com tags inline para
  produzir `labels`. O texto subjacente é sempre 100% real; a contribuição do LLM é
  só a decisão de segmentação.
- **Técnica 2 — aumento sintético de âncoras** (esta seção): o LLM é apresentado a um
  lote de exemplos reais de uma categoria específica (spans já anotados dessa
  categoria, extraídos de `annotations/`) e pedido para **gerar** novos exemplos
  curtos da mesma categoria. O texto gerado não é real — é conteúdo novo, sintético.

A Técnica 2 é permitida antes de um baseline real (exceção do §3.4) porque seu escopo é
estreito o bastante para o risco ser administrável sem um gate de avaliação completo:
gera variação de **frase-âncora** (1–5 palavras, a mesma granularidade de categoria do
§11), nunca um documento inteiro. O risco que essa granularidade não elimina — um LLM
pedido para "gerar mais exemplos assim" a partir de um lote pequeno tende a produzir
frases mais estereotipadas do que a variação real dos documentos (ruído de OCR,
formulações incomuns de cartórios/varas específicas) — é administrado por três
salvaguardas obrigatórias, não por medição contra holdout:

1. **Sempre marcado, nunca real por omissão.** `DocumentRecord.source.system` e
   `AnnotationRecord.annotation_method` de um registro produzido pela Técnica 2
   identificam-no explicitamente como gerado (ex.: `system="llm_span_augmentation"`,
   `annotation_method="llm_span_augmentation"`) — nenhum campo novo de schema é
   necessário, os campos já existem para isso. Um consumidor do dataset nunca precisa
   adivinhar a proveniência de um registro.
2. **Excluído das contagens de suporte real.** O piso `train_minimum_support_per_category`
   (§5.4, gate rígido do §12.1) conta só registros cuja proveniência não é
   `llm_span_augmentation` — a Técnica 2 nunca pode fazer uma categoria parecer mais
   bem suprida de dados reais do que realmente está. Volume sintético, se reportado, é
   uma contagem separada no manifest, nunca somada à contagem real.
3. **Train-only por construção, não por regra adicional.** Um registro da Técnica 2 não
   tem adjudicação independente (não pode ter — não há um segundo anotador real
   concordando sobre um span que não existia antes), então já é estruturalmente
   inelegível para validação/teste pela política de elegibilidade do §10 — nenhuma
   verificação extra é necessária além da que já existe.

Registros da Técnica 2 continuam sujeitos a toda validação mecânica do §11 (offsets,
não-sobreposição, pertencimento à ontologia) — a exceção do §3.4 é sobre **quando** o
dado pode ser usado, nunca sobre **se** ele precisa ser mecanicamente válido.

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

- schema válido (estrutura e atributos do XML por registro — documento/anotação/
  review —, §8);
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

Note que fidelidade verbatim (texto reconstruído das tags inline == `document.text`)
não está nesta lista: não é um invariante rígido de release. O `SegmenterDatasetStore`
já é seguro por construção nesse ponto — `write_annotation` reconstrói as tags a partir
do `document.text` já confiável, nunca do texto bruto que um anotador-LLM digitou; a
saída bruta de um LLM nunca chega ao store diretamente. Ferramentas futuras que
convertem essa saída bruta em `AnnotationRecord` (fora do escopo deste PR) devem
comparar o texto reconstruído contra o documento-fonte, mas um descasamento é um
**sinal de risco** que escalona para revisão independente (§9, "Dados de treino"),
não uma rejeição automática do registro.

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

```csv
gate,status,reason
minimum_tribunal_count,known_limitation,Release inicial é explicitamente TJRO-only
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

As linhas do split de teste versionadas em texto claro nas tabelas CSV públicas do
repositório não estão trancadas — qualquer sessão de desenvolvimento pode lê-las a
qualquer momento. O trancamento é
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

- **Baseline trivial e pisos críticos: regra fixada no §5.6, não uma margem que o
  release declara por conta própria.** Comparação, no mesmo teste trancado, contra um
  extrator heurístico/determinístico já existente (ex.: os extratores de fronteira do
  PR 2/§18) ou, na ausência de um, contra predição por classe majoritária; elegível a
  deploy apenas se o limite inferior do IC 95% da **diferença** (modelo − baseline),
  bootstrap sobre documentos, for **> 0** — não uma margem arbitrária que poderia ser
  pré-declarada perto de zero. As categorias operacionalmente críticas
  (`dispositivo_abertura`, `resultado`, `acordao_decisorio_inicio`,
  `acordao_decisorio_fim`) têm piso de macro-F1 (ponto estimado) ≥ 0.5, fixado no §5.6
  para v8.1 — não escolhido pelo release antes da avaliação de teste. Falhar um piso
  crítico bloqueia o deploy mesmo com macro-F1 agregado aceitável — não há trade-off
  implícito entre categorias críticas e não;
- **Intervalo de confiança no resultado de teste**: bootstrap sobre documentos (mesma
  metodologia do §8), obrigatório dado o tamanho pequeno do teste (§5.4). Um F1 pontual
  sem IC não é uma alegação aceitável de desempenho;
- essas evidências (diferença vs. baseline com IC, pisos por categoria) compõem o
  **model card** publicado junto ao checkpoint, distinto do manifest de dataset.

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
