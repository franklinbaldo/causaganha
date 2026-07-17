# RFC 0012 — Segmentador v8: dataset confiável e baseline honesto com dados reais

- **Status:** Proposto
- **Data:** 2026-07-17
- **Depende de:** RFC 0001 (segmenter v7 finetuning/diagnóstico), RFC 0003 (JURIS TJRO
  como fonte de documentos reais)
- **Relação com RFC 0011 / PR #831 / PR #832:** esta RFC **substitui a fundação** do
  plano sintético. A RFC 0011 (gerador sintético) deixa de ser a base do segmentador e
  passa a ser a **camada experimental da Fase 5** (§15, PR 5), condicionada à existência
  do baseline real desta RFC. O PR #832 não deve ser mergeado como está; seus ativos são
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

### 3.1 Um estado de dataset representa uma garantia real

O sistema reconhece cinco estados distintos:

1. **Candidato** — spans extraídos ou propostos. Nenhuma alegação de qualidade.
2. **Anotado** — uma anotação completa produzida por um anotador.
3. **Adjudicado** — revisado independentemente ou resolvido por adjudicação explícita.
4. **Split-assigned** — atribuído a train/val/test após checagens de vazamento.
5. **Released** — artefato imutável, com checksums, aprovado para um uso declarado.

Nenhuma operação pode renomear um estado para outro sem adicionar a garantia que o novo
estado representa.

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

O primeiro baseline de produção usa apenas documentos reais adjudicados. Dados
sintéticos, aumentados e híbridos são fontes experimentais: só entram no treino via
ablações controladas **depois** do baseline real estar congelado.

### 3.5 Todo waiver é estreito

Um waiver de diversidade de tribunal não pode desabilitar salvaguardas não
relacionadas. Cada regra de prontidão tem status independente e waiver
independentemente configurável, com justificativa registrada. Não existe
`--skip-gates` genérico (a versão all-or-nothing do PR #832 é exatamente o
antipadrão que este princípio proíbe).

## 4. Objetivos do primeiro release

- definir uma ontologia canônica (decisão em §5);
- construir um corpus real adjudicado;
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

1. **Ontologia v8 = ontologia v7 congelada**, sem adição ou remoção de categorias.
   `ref_normativa` permanece fora do espaço treinável (RFC 0001: pré-passe regex na
   inferência). A ambiguidade conhecida do heading de `preliminar` ("1. PRELIMINARES"
   vs "PRELIMINAR REJEITADA" como palavra de resultado) é tratada na guideline de
   anotação, não na ontologia. Qualquer mudança de ontologia invalida anotações
   existentes e exige nova RFC.
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
4. **Metas de suprimento do primeiro release:** ≥ 150 docs de treino adjudicados,
   ≥ 30 de validação, ≥ 30 de teste, com suporte mínimo por categoria herdado do gate
   G2 vigente (≥ 10 ocorrências por categoria treinável no treino; ≥ 5 em validação
   para reportar métrica por categoria). Val/test custam ~3× o treino (duas anotações
   independentes + adjudicação); a meta é deliberadamente modesta.
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

- **Mantenedor do dataset** — extrai candidatos, coordena anotação, adjudica conflitos,
  cria releases.
- **Desenvolvedor de modelo** — treina contra releases imutáveis e seleciona
  configurações por resultados de validação.
- **Revisor** — verifica qualidade de anotação, integridade de splits, proveniência e
  metodologia de avaliação.
- **Consumidor de produção** — carrega um modelo com ontologia documentada, linhagem de
  dataset e escopo de avaliação conhecido.

## 8. Artefatos canônicos

Diretórios separados por estado de ciclo de vida:

```text
data/segmenter/
  candidates/
  annotations/
  adjudications/
  splits/
  releases/
```

### Registro de candidato

```json
{
  "candidate_id": "stable-id",
  "document_id": "source-document-id",
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
  "candidate_id": "stable-id",
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

### Registro de adjudicação

```json
{
  "candidate_id": "stable-id",
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
  "ontology_version": "segmenter-v8",
  "guideline_version": "segmenter-v8-guideline-1",
  "source_commit": "full-git-sha",
  "split_hashes": { "train": "...", "validation": "...", "test": "..." },
  "counts": {},
  "tribunals": {},
  "document_types": {},
  "annotation_quality": {
    "val_iaa_span_f1": null,
    "test_iaa_span_f1": null,
    "per_category_iaa": {}
  },
  "waivers": [],
  "created_at": "..."
}
```

**`annotation_quality` é obrigatório e definido**: concordância inter-anotador (IAA) em
nível de span — F1 entre as duas anotações independentes, computado **antes** da
adjudicação, agregado e por categoria, para val e test. É a versão falsificável de
"qualidade de anotação"; um release de eval sem IAA reportado não passa no gate
correspondente (§14).

## 9. Política de anotação

### Dados de treino

Registros de treino exigem:

- uma anotação completa;
- validação mecânica;
- validação automática de consistência de pares;
- spot-review por amostragem de risco.

Registros de alto risco recebem revisão independente. Sinais de risco:

- spans candidatos sobrepostos;
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

## 10. Política de splits

Atribuição de split acontece **somente após adjudicação**.

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
- todos os campos de proveniência exigidos pelo estado presentes.

A validação mecânica roda **in-process** (biblioteca), não via chamadas repetidas de
subprocesso a `opf_annotate.py`.

## 12. Comando de release

A operação chama-se:

```text
build_gold_release
```

Ela **não promove candidatos** — empacota registros já adjudicados e split-assigned:

1. carrega adjudicações;
2. verifica integridade de splits;
3. valida cada registro;
4. calcula contagens e hashes;
5. checa regras de prontidão configuradas independentemente;
6. escreve em diretório temporário;
7. verifica o release escrito;
8. renomeia atomicamente para o release ID final;
9. recusa sobrescrever release existente.

Cada waiver identifica exatamente uma regra:

```json
{
  "gate": "minimum_tribunal_count",
  "status": "waived",
  "reason": "Release inicial é explicitamente TJRO-only",
  "approved_by": "...",
  "expires_after_release": "segmenter-real-v8.1"
}
```

Não existe `--skip-gates` genérico.

## 13. Treino baseline e avaliação de teste

O primeiro baseline usa: split de treino real adjudicado; validação congelada; uma
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

Aprendizados mecânicos do PR #832 que **permanecem válidos** para o runner: processo
por época com resume via `--checkpoint` (o trainer do `opf` vaza RAM em processo
longo), e os hiperparâmetros do sweep (lr 5e-5, batch 1, grad-accum 4) como ponto de
partida — não como configuração congelada.

## 14. Gates de prontidão

Cada gate tem resultado independente.

**Exigidos para treino baseline:**

- schema de ontologia válido;
- train/val/test disjuntos por grupo, ID e hash exato;
- nenhum conflito de anotação não resolvido;
- todo registro de val/test com duas anotações independentes + adjudicação;
- IAA de val/test computado e publicado no manifest (§8);
- suporte mínimo de treino por categoria (§5.4);
- suporte mínimo de validação para métricas reportadas;
- checksums de release gerados;
- working tree Git limpa;
- SHA Git completo registrado.

**Exigidos para alegações amplas de produção:**

- múltiplos tribunais;
- múltiplos sistemas-fonte;
- diversidade temporal;
- conjunto de avaliação representativo;
- anotação de teste externa ou revisada independentemente.

Um modelo TJRO-only **pode** ser lançado, mas nomeado e descrito como TJRO-específico.

## 15. Plano de implementação

**PR 1 — Ciclo de vida canônico do dataset.** Schemas de registro; diretórios de
candidatos/anotações/adjudicações; IDs determinísticos e hashes de conteúdo;
documentação do ciclo de vida. Sem treino, sem sintético.

**PR 2 — Validação e construtor de splits.** Validação de pares; checagens cross-split
por ID/hash; clustering de duplicatas; splitter determinístico por grupo; testes de
vazamento e rótulos malformados. Reaproveita `transform.py`, `dedup.py`,
`split_guard.py`, `validators.py`, `provenance.py` do PR #832 (com os fixes da review).

**PR 3 — Construtor de release imutável.** `build_gold_release`; gates e waivers
independentes; saída atômica; manifest completo (incl. IAA); checksums e verificação
de árvore limpa.

**PR 4 — Trainer do baseline real.** Um runner de treino; seleção de checkpoint só por
validação; manifest de experimento; avaliação de teste única e trancada.

**PR 5 — Experimentação sintética (RFC 0011 revisada).** Só após PRs 1–4 produzirem um
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
sem degradar materialmente categorias críticas. O teste permanece trancado durante
todos esses experimentos.

## 16. Critérios de aceitação do primeiro release

O trabalho está completo quando:

- todo registro de val/test tem duas anotações independentes e um registro de
  adjudicação;
- nenhum grupo de documentos, duplicata exata ou quase-duplicata conhecida atravessa
  splits;
- todo rótulo passa nas regras semânticas de par e na validação mecânica;
- um release é imutável e reprodutível a partir de um commit Git limpo;
- o checkpoint é selecionado só por macro-F1 de validação;
- o teste é avaliado uma vez, após congelamento da configuração;
- toda alegação publicada declara escopo de tribunal e fonte;
- nenhum registro sintético é necessário para o primeiro baseline confiável;
- outro desenvolvedor consegue reproduzir release, treino e métricas apenas com as
  instruções do repositório.

## 17. Métrica de sucesso

O primeiro sucesso não é o F1 mais alto possível. É um resultado cuja linhagem,
qualidade de anotação, integridade de splits e procedimento de avaliação são fortes o
suficiente para que o F1 reportado signifique o que aparenta significar.

## 18. Disposição dos ativos do PR #832

| Ativo do PR #832 | Destino nesta RFC | Disposição |
|---|---|---|
| `transform.py`, `dedup.py`, `split_guard.py`, `validators.py`, `provenance.py` + testes | PR 2 | Reaproveitar com os fixes da review — é o melhor código do PR |
| Extratores JURIS (`juris_extract_gold_candidates.py`, internal-search, preliminar, âncoras únicas) | PR 1 (geração de candidatos) | Reaproveitar como estão: a saída deles **é** o estado "candidato" |
| 131 docs das rodadas A–F | `candidates/` + `annotations/` | Rebaixar: docs de anotação única viram *anotados* (elegíveis a treino); docs assistidos por modelo são treino-only, permanentemente inelegíveis para val/test |
| Seed original de 20 docs (val/test com ensemble) | Mais próximo de *adjudicado* | Re-expressar a verificação ensemble como registros de adjudicação; utilizável como validação, **nunca** como teste (§5.2) |
| Stack sintético (`renderer`, `phrase_banks`, `hybrid`, `llm_content`, `llm_judge`, `diagnostics`, `compose_mix`) | PR 5 apenas | Estacionar sem merge ou mergear atrás de fronteira "experimental"; os phrase banks têm valor independente (codificam achados do corpus real) |
| Aprendizados do runner Kaggle (processo-por-época, hiperparâmetros) | PR 4 | Manter a mecânica; descartar o checkpoint selecionado e o número 0.567 |
| RFC 0011 (PR #831) | Fase 5 | Sobrevive como design doc da camada experimental, subordinada a esta RFC |
