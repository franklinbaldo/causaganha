# Plano — otimizar os Parquets consolidados para storage e leitura no IA

**Data:** 2026-06-07
**Contexto:** o schema de consolidação foi unificado numa única fonte
(`schema_registry.py`, v`3.0.0`). Era de **10 tabelas**; a tabela `classificacoes`
(classificador keyword-v1, placeholder) está sendo **removida** enquanto a
classificação é redesenhada (PR #784), levando o schema a **9 tabelas**. Este plano
já assume as 9 — qualquer item que dependia de `outcome`/`classificacoes` está
marcado como bloqueado abaixo. As colunas e tipos restantes estão razoáveis, mas a
**camada física** dos Parquets gravados no Internet Archive não está otimizada
para o padrão de acesso real (DuckDB httpfs / WASM via HTTP Range requests).

Este plano ataca cada problema identificado na análise, em ordem de payoff.

## Como os dados chegam no IA hoje (baseline)

- **Item IA** = `djen-{tribunal}-{year}` (ex.: `djen-tjro-2025`). Uma run
  consolida *todos* os ZIPs de um (tribunal, ano) num DuckDB in-memory.
- **Um Parquet por tabela** → 9 arquivos por item (10 antes da remoção de
  `classificacoes`); cada um contém o ano inteiro daquela tabela/tribunal.
- **Opções de escrita:** `COPY … (FORMAT PARQUET, COMPRESSION ZSTD,
  KV_METADATA {schema_version, item_id})`. Sem `ORDER BY`, sem `ROW_GROUP_SIZE`,
  sem `PARTITION_BY` (verificado em `scripts/pipeline/consolidate.py` e
  `src/causaganha/consolidate/exporter.py`).
- **Leitura:** DuckDB lê footer + row groups via HTTP Range.

Princípio orientador: **medir antes de migrar schema**. Mudanças de coluna são
caras (re-upload de itens no IA, bump de versão, quebra de consumidores
DuckDB-WASM). Mudanças de layout físico (ordenação, row-group size) **não quebram
consumidores** e não bumpam o **contrato** de schema — mas **não são de graça**:
aplicá-las ao acervo existente exige **re-upload dos itens** (os bytes do Parquet
mudam) e, hoje, **não há gatilho** que dispare esse reprocessamento sem um bump de
versão (ver "Problema 0 — gatilho de reprocessamento", logo abaixo). Então "sem
bump" significa "sem quebra de consumidor", **não** "sem re-upload".

**Legenda de evidência** (cada sub-item é marcado):

- **[verified]** — confirmado contra código ou comportamento real do DuckDB neste
  repo (com a linha/saída citada).
- **[benchmarked]** — medido com um experimento reproduzível (matriz/numeros neste
  doc).
- **[speculative]** — hipótese plausível, **ainda não medida**; não tratar como
  ganho provado até benchmarkar.

---

## Problema 0 — `schema_version` é gatilho de reprocessamento **e** contrato (bloqueia P1 de chegar ao acervo) ⚠️

**Sintoma [verified no código]:** a reconsolidação é decidida **só** pela string
`schema_version`:

- `dates_at_current_version()` (`candidates.py:142`) → datas já em
  `CURRENT_VERSION` são consideradas **prontas**.
- O backfill **pula** essas datas (`cli.py:399`).
- `reconsolidate` (`cli.py:440`) só reprocessa datas onde
  `version != CURRENT_VERSION` (`candidates.py:150`).
- **Não há flag de força.**

**Consequência:** uma mudança de layout **sem bump** (P1: `ORDER BY`/
`ROW_GROUP_SIZE`) **nunca alcança os itens existentes** — continuam "3.0.0" =
current = pulados. Só consolidações **novas** ganham o layout; o acervo retroativo
fica na ordem-de-transform para sempre. O mesmo vale para a remoção in-place de
`classificacoes` (PR #784): itens "3.0.0" antigos mantêm `classificacoes.parquet`,
novos "3.0.0" não, e `reconsolidate` não toca nos antigos. **Acervo heterogêneo sob
a mesma string de versão.**

A raiz: `schema_version` faz **dupla função** — **contrato do consumidor** (mudou →
WASM/Zod adaptam) **e** **gatilho de reprocessamento** (mudou → reconsolidar). Para
o roadmap de layout valer, os dois têm que ser **separados**.

**Proposta (concreta):**

- **Opção 1 (principled) — `layout_revision` no manifest**, separado de
  `schema_version`. Reconsolidação dispara quando `schema_version != CURRENT`
  **OU** `layout_revision != CURRENT_LAYOUT`. Bumpar `layout_revision` força
  re-layout **sem** quebrar o contrato (mesmo schema; só os bytes mudam).
  - Onde: `consolidation_manifest.py` grava `layout_revision` ao lado de
    `schema_version`; `candidates.py` compara os dois; `schema_registry.py` ganha
    um `CURRENT_LAYOUT`.
- **Opção 2 (cheap/imediata) — flag `reconsolidate --force/--all`** que reprocessa
  itens current-version. Sem mudar manifest; operador-dirigido. Boa para o
  **rollout único** de A1 e para o **backfill da remoção de `classificacoes`**.
- **Recomendado:** Opção 1 para layout rotineiro (rastreável, automático) +
  Opção 2 como ferramenta de mão para o primeiro rollout e o cleanup do #784.

**Custo explícito:** re-layout = **re-upload dos itens tocados ao IA** (os bytes
mudam), com lock por-item + token bucket (`archive.py`). "Sem bump" economiza o
decode/quebra de consumidor, **não** o re-upload.

**Schema bump:** não (infra de pipeline, não muda colunas). **Esforço:** P
(Opção 2) / M (Opção 1). **Payoff:** **Habilita P1/A1 a valer no acervo** — sem
isto, A1 só serve itens futuros.

---

## Problema 1 — Row-group pruning está morto (maior payoff, sem bump) ⚠️

**Sintoma:** os dados são gravados em ordem de transform/hash. As estatísticas
min/max de cada row group abrangem quase o ano inteiro, então uma query por
`data_disponibilizacao` ou `numero_processo` precisa baixar **todos** os row
groups via Range. Paga-se por storage colunar e recebe-se I/O de full table scan.

**Fix:** layout físico, sem bump de schema. `1a` e `1b` são alavancas do `COPY`;
`1c` trata o caso do `numero_processo`, que **não** tem alavanca de `COPY` (ver
abaixo).

### 1a — `ORDER BY` na chave de filtro [verified que falta hoje]

- `comunicacoes` → **chave dominante conforme A0w** (uma chave física por arquivo):
  - se A0w mostrar **range por data** dominante → `.order_by(data_disponibilizacao, numero_processo)`
  - se A0w mostrar **lookup pontual por `numero_processo`** dominante →
    `.order_by(numero_processo, data_disponibilizacao)` (ou índice aditivo, §1c).
  - ⚠️ A chave **secundária só agrupa dentro da primária** — não dá pruning min/max
    global para o segundo predicado. Por isso a escolha da primária tem que vir de
    A0w, não ser fixa.
- `processos` → idem: `.order_by(data, numero_processo)` **ou** `(numero_processo, data)` conforme A0w
- `destinatarios` / `representacoes` / `comunicacao_advogados` → `.order_by(comunicacao_id)`
  (benefício é **pruning ao filtrar por `comunicacao_id`** — joins hash do DuckDB
  não exploram ordenação)
- `advogados` / `advogado_nomes` → `.order_by(nome)` ou `(uf_oab, numero_oab)`
- `textos` → `.order_by(id)` (acesso é por join em `id`)

### 1b — `ROW_GROUP_SIZE` explícito (tuning de granularidade, **não** pré-requisito) — [speculative, precisa benchmark]

⚠️ **`ORDER BY` sozinho já habilita pruning em arquivos com >1 row group.** Não
gate A1 nisto. O default do DuckDB é `ROW_GROUP_SIZE = 122_880` linhas: qualquer
arquivo **acima** desse tamanho já tem múltiplos row groups, então a ordenação
sozinha (A1) cria faixas min/max disjuntas e poda — sem tocar em `ROW_GROUP_SIZE`.
A1 é útil imediatamente; **não** depende do benchmark de A1b.

O caso onde `ORDER BY` **com o `ROW_GROUP_SIZE` default não muda nada** [verified]
é o item **pequeno** que cabe num **único** row group (ex.: `djen-tjro-2025`): há um
só row group cobrindo o ano todo e um Range read baixa tudo. **Mas isso não exclui
o item pequeno de A1b:** reduzir o `ROW_GROUP_SIZE` pode **quebrar esse arquivo
pequeno em vários row groups** e aí a ordenação prévia passa a podar (leituras HTTP
seletivas em vez do arquivo inteiro). Então `ROW_GROUP_SIZE` tem dois papéis: (a)
**habilitar** pruning no item pequeno (que sem ele tem 1 grupo só) e (b) **ajustar
a granularidade** dos itens grandes (faixas min/max mais estreitas), ambos **com
custo**: mais overhead de footer e possível **piora de full scans** (mais row
groups para varrer). A1b deve medir **as duas classes de item** (pequeno e grande).
O valor `16_384` citado antes **não é um default seguro** — é só um ponto de
partida.

**Antes de fixar o valor, rodar um benchmark** [speculative até medir]: comparar
`16K`, `32K`, `64K` e o default (`122_880`) contra arquivos de produção reais,
medindo **separadamente** queries seletivas e full scans, e reportando por caso:
contagem de row groups, tamanho do arquivo, bytes lidos via httpfs e wall-clock.
Escolher o **menor** size que dá ganho de pruning mensurável **sem** degradar o
broad scan. Validar só o `parquet_metadata` (faixas) cobre o lado do pruning, não
o lado do custo.

### 1c — Lookup pontual por `numero_processo`: escolher a chave de ordenação

O outro acesso quente é por `numero_processo` (CNJ de 20 dígitos, alta entropia).
Ordenar por `data_disponibilizacao` **não** agrupa o `numero_processo`, então
min/max não podam nada para esse acesso — e **não dá para ordenar fisicamente o
mesmo arquivo por duas chaves**. Há um trade-off de uma-chave-por-arquivo.

⚠️ **Bloom filter via `COPY` depende da _ordenação_, não da cardinalidade
global.** [benchmarked, DuckDB 1.5.3 fixado no repo] Correção de uma afirmação
anterior cedo demais (que dizia categoricamente "alta cardinalidade → nunca tem
bloom"): o DuckDB **escreve** bloom filter só nos row groups que ele
**dictionary-encoda**, e essa decisão é **por row group**, a partir dos distintos
*dentro daquele grupo* — não da cardinalidade global. Ordenar pela coluna agrupa
uma faixa estreita de valores em cada row group, então uma coluna globalmente de
alta cardinalidade **pode** virar dictionary-encoded (e ganhar bloom) **quando o
arquivo é ordenado por ela**. Não existe sintaxe por coluna (`BLOOM_FILTER(col)` é
rejeitada); o flag global é `WRITE_BLOOM_FILTER true`. Matriz medida — **500K
linhas** fixas, coluna CNJ zero-padded de 20 dígitos, **com coluna `data` real e
`ORDER BY data` explícito** (não shuffle): `data` e `numero_processo` usam strides
coprimos, modelando o real (muitos processos distintos por dia, comunicações de um
processo espalhadas no ano). Script reproduzível:
`scripts/benchmarks/bloom_cardinality.py`:

| ordenação | cardinalidade | `ROW_GROUP_SIZE` | row groups c/ bloom | encoding |
|---|---|---|---|---|
| `ORDER BY data` | 100K | default | 0 / 5 | PLAIN |
| `ORDER BY data` | 100K | 16K | 0 / 31 | PLAIN |
| `ORDER BY numero_processo` | 100K | default | **5 / 5** | PLAIN_DICTIONARY |
| `ORDER BY numero_processo` | 100K | 16K | 1 / 31 | misto |
| `ORDER BY numero_processo` | 500K (único) | default | 0 / 5 | PLAIN |

> ⚠️ **Dados sintéticos, não produção.** O modelo coprimo é uma aproximação do
> acoplamento data↔processo. A correlação real (quantas comunicações por processo,
> quão agrupadas no tempo) muda os distintos por row group e, com eles, a decisão
> de bloom. A conclusão do caso date-ordered tem que ser **confirmada em dados
> reais por A1c** (ver abaixo) — não cravada a partir do sintético, e **não** por
> A0, que só mede arquivos atuais (bytes/cardinalidade/formato) e nunca escreve
> layouts candidatos nem inspeciona bloom por row group. Sem essa confirmação, o
> roadmap pode prescrever um índice covering desnecessário (se na verdade a ordem
> por data **já** rendesse bloom em produção) — ou deixar de prescrevê-lo.

Leitura correta:

- **Arquivo ordenado por data** (caso date-dominant em A0w): `numero_processo`
  fica espalhado → cada row group tem distintos demais → PLAIN, **sem bloom**. O
  lookup pontual paga broad-scan → precisa do índice covering (passo 2 abaixo).
- **Arquivo ordenado por `numero_processo`** (caso CNJ-dominant em A0w): com
  repetição suficiente por grupo, vira dictionary + **bloom em todo row group** —
  e ainda ganha min/max pruning pela própria ordenação. **Mas** se o CNJ for
  **quase único** (poucas comunicações por processo), nem ordenar salva: distintos
  por grupo estouram o limite de dictionary → PLAIN, sem bloom. O fator de
  repetição real (comunicações por processo) tem que ser **medido em A0**.

Ou seja: bloom para CNJ **não é categoricamente inútil** — é condicional à
ordenação por CNJ **e** ao fator de repetição por row group. Onde o arquivo é
ordenado por data, bloom não ajuda e o índice covering é a saída.

Estratégia realista, em ordem:

1. **Ordenar `comunicacoes` pela chave dominante** (provavelmente
   `data_disponibilizacao`, confirmar com os logs de query do dashboard). O outro
   acesso paga full-scan de row groups.
2. **Se o lookup por `numero_processo` for hot o suficiente**, criar um Parquet
   aditivo ordenado por `numero_processo`. ⚠️ **Tem que ser um índice _covering_**,
   não só `(numero_processo → comunicacao_id)`: um índice magro poda o lookup no
   índice, mas depois **junta de volta** no `comunicacoes` ordenado por data — que
   é exatamente o full-scan que se queria evitar. Para entregar a redução de I/O, o
   arquivo precisa carregar **todo o payload da query quente** (as colunas que o
   dashboard lê para esse acesso), de modo que a leitura termine no próprio índice
   sem voltar ao arquivo base. (Alternativa teórica — um locator físico row-group —
   não é praticável com DuckDB-over-HTTP; ficar no covering.) Por ser um **dataset
   novo com schema e contrato de consumidor próprios**, leva um **bump aditivo**
   (igual ao serving — agrupar no mesmo `3.1.0`) e tem que ser **registrado** junto
   às demais tabelas (schema registry + tooling de validação/descoberta), senão
   clientes não têm como saber se o índice existe. Não é "sem bump".
3. A migração `numero_processo` para um **encoding empacotado** (Problema 2 / A3)
   **reduz bytes** — mas **não** melhora a seletividade de min/max. Para CNJs como
   strings de 20 dígitos zero-padded, a ordem lexicográfica já é idêntica à
   numérica, então min/max poda igual com ou sem empacotamento; o ganho de pruning
   vem da **ordenação/índice** (§1a-1b), não do encoding. O encoding só vale por
   tamanho, e só se for empacotado de verdade:

   - `string→BLOB` genérico mantém os 20 bytes ASCII (no-op).
   - **`HUGEINT`/`UHUGEINT` NÃO servem** (verificado no DuckDB 1.5.3): o `COPY`
     mapeia ambos para Parquet `DOUBLE`, então `99999999999999999999` volta como
     `1e+20` — **perde precisão**.
   - **Usar `DECIMAL(20,0)`**: o `COPY` grava como `FIXED_LEN_BYTE_ARRAY` (~16
     bytes < 20 ASCII) e preserva o **valor numérico** lossless (verificado).
     Alternativa: byte array de largura fixa com encoding explícito.
   - ⚠️ **`DECIMAL` perde os zeros à esquerda na decodificação.** [verified, DuckDB
     1.5.3] O CNJ `00000011202580100012` volta como `11202580100012` num
     `CAST(... AS VARCHAR)` ingênuo. O valor numérico é lossless, mas o
     **identificador canônico de 20 chars não é** sem re-padding. **Obrigatório**
     reconstruir com `LPAD(CAST(numero_processo AS VARCHAR), 20, '0')`:
     - no **teste de round-trip** (`COPY` → `read_parquet` → `LPAD(...,20)` →
       comparar com a string original — comparar `d::VARCHAR` cru **falha**);
     - no **contrato WASM** (todo consumidor faz `LPAD`/zero-pad ao reidratar o
       CNJ; sem isso, joins por `numero_processo` e exibição quebram).

   **Validar o formato antes (parte do A0):** o encoding numérico assume 20
   dígitos, mas `_safe()` (ambos os code paths) converte valores ausentes em `''`
   e `validate_ndjson_sample()` só checa presença, não formato (os testes aceitam
   `numero_processo: "x"`). Valores históricos não-numéricos/curtos fazem o cast
   `DECIMAL` falhar. O A0 tem que auditar essa invariante e a migração tem que
   definir um **fallback reversível** — reter o `numero_processo` original como
   string (campo companheiro/variante) para os não-conformes. **Não** usar
   sentinela: colapsa valores distintos, pode colidir com um válido e impede
   reconstruir o original, quebrando a promessa lossless.

**Onde:** o `COPY` é montado em `scripts/pipeline/consolidate.py:1419-1424` e
`src/causaganha/consolidate/exporter.py:57-62` (acrescentar as opções ao
`copy_opts`); o `ORDER BY` vai nos builders `_build_*` de
`scripts/pipeline/consolidate.py` **e** de
`src/causaganha/consolidate/transforms.py` (lógica forkada — mudar nos dois). A
ordenação é uma expressão Ibis lazy — o DuckDB aplica no `COPY` final, sem
materializar em Python.

**Validação (dois níveis):**

1. **Estrutural:** `SELECT stats_min, stats_max FROM
   parquet_metadata('comunicacoes.parquet')` deve mostrar faixas estreitas e
   disjuntas de `data_disponibilizacao` por row group (e >1 row group nos itens
   grandes).
2. **I/O real (prova do payoff):** medir bytes baixados via httpfs para uma query
   representativa do dashboard (`SET enable_http_metadata_cache=true; …`)
   pré/pós. Faixas estreitas no metadata são necessárias mas não suficientes — só
   o byte-count prova que "baixa 1 row group vs. o ano todo".

**Schema bump:** não (A1/A1b). **Esforço:** P (`ORDER BY`) + P-M (benchmark de
row-group); índice aditivo por `numero_processo` é M. **Payoff:** Grande **para
itens grandes**; neutro para itens pequenos de 1 row group. **[A1 verified como
faltante; A1b speculative até benchmarkar.]**

---

## Problema 2 — Chaves UUID gravadas como string de 36 chars (maior custo de tamanho) ⚠️

**Sintoma:** o schema é UUID-keyed em todo lugar (`id`, `original_id`,
`texto_id`, `comunicacao_id`, `advogado_id`, `parte_id`), todos `string`. Um
UUIDv5 em texto são 36 bytes de alta entropia → dictionary/ZSTD rendem pouco. Em
binário (`UUID`/16-byte fixed ou `BLOB`) são ~16 bytes e codificam melhor.
(`winner_advogado_id`/`loser_advogado_id` saíram com a remoção de `classificacoes`,
PR #784.)

**Pré-requisito (NÃO migrar às cegas):** medir primeiro (ver tarefa A0). Decidir
com base em dado:

- Se as chaves UUID dominam os bytes não-texto → migração vale.
- Se `texto` domina → pular (o ganho é ruído).
- **Não esquecer `numero_processo`:** é uma string CNJ de 20 dígitos, alta
  entropia, presente em `comunicacoes` e `processos` [verified — não existe em
  `destinatarios`, cujo identificador é `comunicacao_id`]. Pode pesar **mais** que
  os UUIDs nos bytes não-texto. A medição A0 tem que reportá-la lado
  a lado com as chaves UUID — senão a decisão fica com visão de túnel no UUID e
  ignora a coluna que talvez seja o maior alvo. **Atenção:** ao contrário do UUID
  (que já é 16 bytes em binário), o CNJ só ganha **bytes** (não pruning) e precisa
  de um **encoding empacotado explícito** — `string→BLOB` é no-op e `HUGEINT` vira
  `DOUBLE` (perde precisão). Ver §1c passo 3 para a representação correta
  (`DECIMAL(20,0)`), o **re-padding com `LPAD(...,20,'0')`** (DECIMAL perde zeros à
  esquerda), o round-trip e o fallback de formato.

**Fix (se confirmado):** mudar UUIDs de `string` → tipo binário no registry.
Isto é um **bump major (4.0.0)** e força todo consumidor DuckDB-WASM a `decode`.
Implementação:

1. `schema_registry.py`: nova `SCHEMA_V4` com chaves binárias; `CURRENT_VERSION`.
2. Builders: `djen_uuid5(...)` retorna binário 16-byte em vez de string.
3. `validation.py`: invariantes de tipo atualizadas.
4. Zod/frontend: schema `v4` + decode helper.
5. Reconsolidação seletiva (datas `schema_version < CURRENT`).

**Schema bump:** sim (major). **Esforço:** M. **Payoff:** Grande *se* medição confirmar.

---

## Problema 3 — JOINs cross-file pagam latência HTTP por arquivo

**Sintoma:** as tabelas normalizadas são limpas como forma canônica, mas o
DuckDB-over-HTTP paga footer + Range reads por arquivo a cada JOIN. A query
"advogado → comunicações com outcome" seria um join de 4 tabelas
(`comunicacao_advogados` × `comunicacoes` × `classificacoes` × `advogados`).

> ⛔ **Bloqueado em dobro — não é acionável agora.**
> 1. **A fonte de `outcome` saiu do schema.** O serving denormaliza
>    `outcome`/`decision_type`/`confidence`, que vinham de `classificacoes` —
>    tabela **removida** (PR #784) enquanto a classificação é redesenhada. Sem ela
>    não há outcome para servir. Este problema **só volta à mesa quando a
>    classificação retornar ao schema** (e seu shape final define o serving).
> 2. **O consumidor não existe** [verified no código]. Mesmo com outcome, o join
>    de 4 tabelas **não existe** no frontend: `web/src/components/
>    DuckDBExplorer.svelte` opera sobre **um** item `(tribunal, ano)` por vez, sem
>    `union_by_name` cross-item, e faz no máximo um join de **2** tabelas. O
>    serving *habilita* um fluxo planejado, não elimina leituras de um load path
>    existente.

**Fix (quando desbloquear):** Parquet-per-access-pattern (ficha ADR 0008). Manter
as tabelas normalizadas como **canônicas** e adicionar um Parquet de **serving**
denormalizado, modelado na query quente, gerado no fim da consolidação por uma
expressão Ibis de join. O shape exato (quais colunas de outcome) depende do
desenho final da classificação. É **por item** `(tribunal, ano)` — 1 arquivo em
vez de 4 *por item*, não um arquivo global.

**Pré-requisito honesto:** (1) classificação reintroduzida no schema **e** (2) o
fluxo de consumo que faz o join. Planejar os três juntos ou não priorizar.

**Schema bump:** patch (tabela nova, aditiva). **Esforço:** M (Parquet) + M
(consumidor). **Payoff:** Grande **se** classificação voltar **e** o consumidor for
construído; nulo isolado.

---

## Problema 4 — Colunas constantes redundantes por arquivo

**Sintoma:** como o item é um (tribunal, ano), `tribunal`, `p_ano` e
`p_item_ia` são **constantes** dentro de cada arquivo. ZSTD+RLE comprime para
quase nada (custo de storage desprezível), mas são ruído de schema e `p_item_ia`
duplica info já presente no `KV_METADATA` (footer) e no nome do arquivo.

**Fix:**

- Manter `tribunal` e `p_ano` — queries cross-item (`union_by_name`) usam para
  filtrar/agrupar.
- `p_item_ia`: **candidato a remoção, não remoção certa.** A info já está em
  `kv_metadata.causaganha.item_id` (footer) e no path do item. **Mas:** o ganho de
  storage é provavelmente ínfimo (a própria análise diz que comprime "para quase
  nada" via RLE), e remover troca um **campo queryable** por algo que o consumidor
  teria que reconstruir do footer/path — é mudança de schema/API, não limpeza
  pura. **Pré-requisito:** auditar consumidores (frontend, scripts, queries `.qmd`,
  debugging ad-hoc) e só remover se nenhum usar `p_item_ia` como coluna. Se
  remover, documentar quais workflows perdem o acesso direto e como recuperam a
  proveniência (ler `kv_metadata`).

**Schema bump:** sim (major — remoção de coluna), **se** a auditoria liberar.
Agrupar com o Problema 2 no mesmo `4.0.0` para não pagar dois re-uploads.
**Esforço:** P. **Payoff:** Pequeno (storage ínfimo; o valor real é só reduzir
ruído de schema).

---

## Problema 5 — Ajustes finos de tipo

**Sintoma:** ganhos pequenos, agrupar com outro bump.

- `hash` é texto de alta cardinalidade que comprime mal — avaliar se precisa
  viver no store colunar, ou se pode ser binário como os UUIDs.

> Nota: o antigo item `confidence float64 → float32` **saiu** — `confidence` só
> existia em `classificacoes`, removida (PR #784). Se a classificação voltar com
> um campo de confiança, reavaliar `float32` então.

**Schema bump:** sim — juntar com `4.0.0`. **Esforço:** P. **Payoff:** Pequeno.

---

## Ordem de execução

Duas trilhas independentes. **A** é trabalho de storage validável (medir → aplicar
→ provar). **B** é feature de produto especulativa, **gated** por um consumidor que
ainda não existe — não fica no caminho crítico de storage.

### Trilha A — storage validado (storage roadmap)

| # | Tarefa | Bump? | Esforço | Payoff |
|---|--------|-------|---------|--------|
| A0 | Medição **de storage**: baixar **vários** itens (tribunais/anos de tamanhos diferentes) do IA + `parquet_metadata()` por coluna, em **todas** as tabelas largas. Reportar bytes por coluna (UUIDs **e** `numero_processo`), cardinalidade, e **auditar o formato de `numero_processo`** (quantos não são 20 dígitos). Script: `scripts/benchmarks/column_storage.py`. | não | P | Habilita A0e/A4/A5 |
| A0w | Medição **de workload** (gate de A1): coletar a frequência de query por predicado — `data_disponibilizacao` (range) vs `numero_processo` (pontual) — dos logs do dashboard/explorador. **Surface: DuckDB-WASM `read_parquet()` in `DuckDBExplorer.svelte` + `DataAccessPanel.svelte` — the only HTTP query path. Static JSON (`.qmd` contracts) does NOT query Parquets over HTTP.** A1 ordena por **uma** chave; ordenar pela errada deixa a outra em full-scan. | não | P | **Gate de A1** |
| A0e | ✅ **Script written** (`scripts/benchmarks/encoding_comparison.py`) Benchmark **de encoding** (gate de A2/A3): compare v3 strings vs v4 binary candidates (UUID→blob, CNJ→DECIMAL(20,0), hash→bytes). Synthetic mode available without IA access; run `--real-file` against production Parquets before deciding. | não | P-M | **Gate de A2/A3** |
| A1 | ✅ **DONE (PR #785)** Layout físico no `COPY` (ambos os code paths): **1a** `ORDER BY` pela chave dominante — `data_disponibilizacao` para `comunicacoes` (A0w pending, assumed dominant). `exporter.py` `_TABLE_ORDER_KEYS` dict covers all 9 tables; whitelist guard enforces completeness. | não | P | **Grande** (itens grandes) |
| A-rev | ✅ **DONE (PR #785)** `layout_revision` field in `ManifestItem` + `CURRENT_LAYOUT_REVISION = "1"` in `schema_registry.py`. `dates_needing_reconsolidation()` catches stale layout. `reconsolidate --force` added as escape hatch (`all_consolidated_dates()`). | não | P-M | **Habilita A1 retroativo** |
| A1b | ✅ **Script written** (`scripts/benchmarks/row_group_size.py`) Benchmark de `ROW_GROUP_SIZE` (8K/16K/32K/64K/default) in synthetic small/medium/large item classes. Run against production files before setting a non-default value. [speculative até medir em produção] | não | P-M | Grande se confirmado |
| A1c | **Gate da decisão de §1c** (índice covering): em **dados reais**, escrever os layouts candidatos (`ORDER BY data` e `ORDER BY numero_processo`) e inspecionar `parquet_metadata` por **encoding e `bloom_filter_offset` por row group** + provar com byte-count httpfs de um lookup pontual por `numero_processo`. Confirma se a ordem por data realmente não rende bloom (→ precisa do índice covering) ou se rende (→ índice dispensável). Substitui a extrapolação do benchmark sintético. [speculative até medir em produção] | não | P | **Gate do índice covering** |
| A2 | (se **A0e** confirmar economia, não só dominância em A0) UUID `string → 16-byte` no registry. **SCHEMA_V4 parked** in `schema_registry.py` (not active). **Contrato WASM:** ler `BLOB`/`UUID` 16-byte → `uuid.stringify`. **Pré-req de rollback (A-pré):** ✅ `scripts/snapshot_parquets_for_rollback.py` written | major `4.0.0` | M | Grande |
| A3 | (se **A0e** confirmar economia, não só dominância em A0) CNJ `string → DECIMAL(20,0)`. **SCHEMA_V4 parked** — `numero_processo decimal(20,0)` in `schema_registry.py`. [verified: BLOB é no-op; HUGEINT vira DOUBLE/perde precisão; DECIMAL preserva valor mas **perde zeros à esquerda**]. **Só ganha bytes, não pruning.** Exige LPAD + round-trip + fallback. **Pré-req de rollback (A-pré):** ✅ snapshot script written | major `4.0.0` | M | Médio |
| A4 | (se auditoria de consumidores liberar) remover `p_item_ia`. **SCHEMA_V4 parked** — `p_item_ia` already absent from `SCHEMA_V4` definition | major `4.0.0` | P | Pequeno |
| A5 | revisar `hash` (binário?). **SCHEMA_V4 parked** — `hash binary(32)` in `SCHEMA_V4` definition | major `4.0.0` | P | Pequeno |

A2-A5 agrupam-se num único bump `4.0.0` (cada major força re-upload de todos os
itens; não pagar dois).

**Caminho crítico de A:** A0 + A0w → ~~A1~~ ✅ → ~~**A-rev**~~ ✅ → A-pré ✅ → A0e → (A2+A3+A4+A5).
**A-rev é pré-requisito de A1 valer no acervo** (sem ele A1 só atinge itens novos —
Problema 0). **A1b fica fora do caminho crítico** — é tuning independente (§1b) e
roda **em paralelo**; as economias de schema (A2-A5) são gated por A0e (economia
medida), não por A0 sozinho nem por `ROW_GROUP_SIZE`. Se nenhum size menor evitar
regressão de broad-scan, A1b simplesmente mantém o default e a migração v4 segue
mesmo assim.

> **A-pré — artefato de rollback (pré-requisito de A2/A3). ✅ Script written: `scripts/snapshot_parquets_for_rollback.py`.** O
> rollback "reler a versão anterior" **não existia no pipeline anterior**:
> `export_table_sync()` sempre grava `{table}.parquet` e `_upload_consolidated()`
> sobe esse mesmo nome **dentro do mesmo item IA** `djen-{tribunal}-{ano}`; o
> manifest de consolidação só registra a versão corrente. Quando o v4 sobrescreve
> os arquivos, **não sobra URL endereçável por versão** do v3 para reler — a
> imutabilidade-por-versão que eu havia afirmado é falsa. Antes de prometer
> rollback, implementar **uma** destas: (a) nomes de arquivo versionados
> (`{table}-v4.parquet`), (b) itens versionados (`djen-{tribunal}-{ano}-v4`), ou
> (c) um procedimento explícito de restauração (snapshot do v3 antes do
> re-upload). Sem isso, A2/A3 são **irreversíveis** na prática.

### Trilha B — serving/consumidor (product-gated, opcional)

| # | Tarefa | Bump? | Depende de | Payoff |
|---|--------|-------|-----------|--------|
| B0 | **Classificação reintroduzida no schema** (redesenho pós-PR #784) — define o shape do `outcome` que o serving denormaliza | — | redesenho da classificação | desbloqueia B1/B2 |
| B1 | **Decisão de produto:** construir o fluxo frontend "advogado → comunicações com outcome" (join de 4 tabelas, hoje inexistente) | — | **B0** + priorização de produto | habilita B2 |
| B2 | Parquet de serving denormalizado | patch aditivo | **B0 + B1** | Grande **só** com B0+B1 |

B só vale com B0 **e** B1. **Sem B0** (sem classificação no schema) **não há
outcome para servir**; sem B1, é storage extra sem consumidor. Nada da Trilha B é
pré-requisito da Trilha A.

**Quick win imediato:** A1 — `ORDER BY` sozinho **já** poda em arquivos com >1 row
group (itens grandes), sem depender de A1b. `ROW_GROUP_SIZE` **não** é exclusivo do
item pequeno: ele muda a **granularidade de pruning, o overhead de footer e o
comportamento de scan dos arquivos grandes** que já têm múltiplos grupos — é
justamente por isso que A1b mira esses itens; e, num arquivo pequeno, pode
**quebrá-lo em vários grupos**. O único caso onde a **ordenação** (A1) é no-op
[verified] é o item pequeno de 1 row group. Não dá para cobrir
`data_disponibilizacao` *e* `numero_processo` na mesma ordenação — escolher a chave
dominante **via A0w** e, se preciso, um índice aditivo covering (bloom filter só
ajuda CNJ se o arquivo for ordenado por CNJ **e** houver repetição por row group,
§1c). Provar o ganho com byte-count httpfs, não só com `parquet_metadata`.

## O que NÃO fazer

- **Não migrar UUID nem CNJ sem medir (A0).** São decisões **separadas** (formas de
  dado diferentes). Se `texto` domina os bytes, o ganho é ruído e o custo (bump
  major + decode no WASM) não compensa. Medir várias tabelas, UUIDs **e**
  `numero_processo`, senão a decisão fica enviesada.
- **Não assumir que A1 chega ao acervo (Problema 0).** [verified] A reconsolidação
  dispara só por `schema_version`; mudança de layout sem bump **pula** todo item
  já em current-version. A1 sem A-rev (`layout_revision`/`--force`) só beneficia
  itens novos. E lembrar: re-layout = re-upload (os bytes mudam) — "sem bump" não é
  "sem re-upload".
- **Não confiar em `ORDER BY` sozinho (A1).** Sem `ROW_GROUP_SIZE`, itens
  pequenos ficam com 1 row group e a ordenação não poda nada. **E não fixar 16K
  como default** — benchmarkar (A1b) o custo de full scan, não só o pruning.
  Validar com byte-count httpfs, não só com `parquet_metadata`.
- **Não assumir bloom filter para `numero_processo` *no arquivo ordenado por
  data* (§1c).** [benchmarked] Bloom só é escrito em row group dictionary-encoded;
  ordenando por data o CNJ espalha → PLAIN → sem bloom. Bloom **só** ajuda CNJ se o
  arquivo for ordenado por CNJ **e** houver repetição suficiente por row group
  (medir em A0) — não é categórico nas duas direções.
- **Não fazer o serving (B2) sem (B0) classificação no schema e (B1) o
  consumidor.** O serving denormaliza `outcome`, que saiu com `classificacoes`
  (PR #784), e o join de 4 tabelas não existe no frontend. É trilha separada, não
  caminho crítico de storage.
- **Não reshapear as tabelas canônicas** para o serving. Adicionar Parquet
  aditivo; manter o modelo normalizado como fonte.
- **Não remover `p_item_ia` sem auditar consumidores (A4).** Storage ganho é
  ínfimo; é troca de campo queryable por reconstrução via footer/path.
- **Não fazer dois bumps majors separados.** Agrupar A2-A5 em `4.0.0` —
  cada bump força re-upload de todos os itens no IA (sem update parcial).
- **Não esquecer o code path legado.** `consolidate-parquet.yml` roda
  `scripts/pipeline/consolidate.py`; toda mudança de layout precisa estar lá
  *e* em `transforms.py`/`exporter.py` (hoje os schemas já são compartilhados via
  registry, mas a lógica de `ORDER BY`/serving é por-builder).
