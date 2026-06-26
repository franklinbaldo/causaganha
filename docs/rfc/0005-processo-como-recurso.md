# RFC 0005 — Processo como recurso unificado (reconciliação DJEN × JURIS × STJ)

- **Status:** Proposto
- **Data:** 2026-06-26
- **Depende de:** RFC 0002 (STJ), RFC 0003 (TJRO JURIS), RFC 0004 (embeddings)
- **Escopo:** Modelo de dados, pipeline de reconciliação e contrato de UI para
  tratar o **processo judicial** (identificado pelo número CNJ) como o recurso
  central do causaganha, agregando contribuições das três fontes — DJEN,
  TJRO JURIS e STJ — em uma visão unificada.

## 1. Resumo executivo

O número CNJ (20 dígitos) é a chave natural que atravessa as três fontes:

| Fonte | Campo | Exemplo |
|---|---|---|
| DJEN | `numero_processo` | `70309694720248220001` |
| TJRO JURIS | `nr_processo` | `70309694720248220001` |
| STJ | `numeroProcesso` | `70309694720248220001` |

Hoje cada fonte vive em silo. Este RFC propõe:

1. Uma **tabela `processos_unificados`** em DuckDB/Parquet que reúne, por
   número CNJ, todas as contribuições de cada fonte.
2. Um **pipeline de reconciliação** (`scripts/reconcile_processos.py`) que
   popula e mantém essa tabela.
3. Uma **query contract** (`web/src/queries/processo.qmd`) que expõe a visão
   unificada para o frontend.
4. Um **endpoint de detalhe de processo** no dashboard (`/processo/{cnj}`) que
   exibe os recursos de cada fonte lado a lado.

O número CNJ normalizado (sem máscara, 20 dígitos) é a chave primária de
`processos_unificados` e o identificador canônico de URL do recurso.

## 2. Motivação

Um processo pode gerar eventos nas três fontes:

```
DJEN        → caderno diário com a publicação da intimação/decisão
TJRO JURIS  → acórdão/sentença indexado no sistema de jurisprudência
STJ         → espelho de acórdão com tese repetitiva, quando o caso sobe
```

Sem reconciliação, um usuário que busca o processo `7030969-47.2024.8.22.0001`:

- No DJEN: vê as datas de publicação no caderno diário, mas não a decisão.
- No JURIS: vê o conteúdo da decisão, mas não sabe quando foi publicado.
- No STJ: vê a tese estabelecida, mas não o histórico em Rondônia.

Com `processos_unificados`, a resposta é:
> "Este processo teve 3 publicações no DJEN (datas X, Y, Z), 2 documentos
> no JURIS (acórdão + voto), e chegou ao STJ onde fixou o tema 1234."

## 3. Modelo de dados

### 3.1 Tabela `processos_unificados`

Chave primária: `nr_processo` (string, 20 dígitos sem máscara).

```
nr_processo          : string     PK — número CNJ normalizado (20 dígitos)
nr_processo_mascara  : string     — NNNNNNN-DD.AAAA.J.TR.OOOO (display)

-- Contribuições DJEN
djen_primeira_pub    : date       — data da primeira publicação no caderno
djen_ultima_pub      : date       — data da publicação mais recente
djen_n_publicacoes   : int32      — total de publicações no DJEN
djen_tribunais       : string[]   — lista de tribunais onde apareceu

-- Contribuições TJRO JURIS
juris_n_documentos   : int32      — total de documentos no acervo JURIS
juris_tipos          : string[]   — tipos presentes (ACÓRDÃO, SENTENÇA…)
juris_data_julgamento: date       — data do julgamento mais recente
juris_orgao          : string     — órgão julgador do acórdão principal
juris_relator        : string     — relator do acórdão principal
juris_classe         : string     — classe judicial
juris_url            : string     — URL do portal JURIS

-- Contribuições STJ
stj_id               : string     — id do espelho no dataset STJ
stj_classe           : string     — siglaClasse no STJ
stj_relator          : string     — ministroRelator
stj_tema             : string     — número do tema repetitivo (se houver)
stj_tese             : string     — teseJuridica (texto completo)
stj_ementa           : string     — ementa resumida
stj_data_decisao     : date       — dataDecisao no STJ
stj_data_publicacao  : date       — dataPublicacao no DJE/STJ

-- Metadados
fontes               : string[]   — ["djen","juris","stj"] (fontes presentes)
n_fontes             : int32      — count de fontes (1, 2 ou 3)
updated_at           : timestamp  — última vez que alguma fonte foi atualizada
```

### 3.2 Tabela auxiliar `processo_documentos`

Para não perder a cardinalidade n:1 (um processo tem vários documentos JURIS):

```
nr_processo   : string   FK → processos_unificados
fonte         : string   "djen" | "juris" | "stj"
id_documento  : string   chave primária da fonte
tipo          : string   tipo de documento na fonte
data          : date     data relevante (publicação/julgamento)
url           : string   URL de acesso ao documento
resumo        : string   ementa/trecho (max 500 chars)
```

### 3.3 Normalização do número CNJ

Todos os números são normalizados antes de qualquer join:

```python
def normalizar_cnj(n: str) -> str:
    """Remove tudo que não é dígito; retorna string de 20 dígitos ou '' se inválido."""
    d = re.sub(r"\D", "", n or "")
    return d if len(d) == 20 else ""

def formatar_cnj(n: str) -> str:
    """20 dígitos → NNNNNNN-DD.AAAA.J.TR.OOOO."""
    if len(n) != 20:
        return n
    return f"{n[0:7]}-{n[7:9]}.{n[9:13]}.{n[13:14]}.{n[14:16]}.{n[16:20]}"
```

Processos com número CNJ inválido (menos de 20 dígitos após stripping)
são descartados do join mas mantidos nas tabelas de origem.

## 4. Pipeline de reconciliação

### 4.1 Script `scripts/reconcile_processos.py`

```
1. Carregar DJEN
   └── DuckDB: ler parquet consolidado `comunicacoes`
   └── GROUP BY nr_processo → (primeira_pub, ultima_pub, n_publicacoes, tribunais[])

2. Carregar JURIS
   └── DuckDB: ler parquets `tjro-juris-AAAA-dedup.parquet`
   └── GROUP BY nr_processo → (n_documentos, tipos[], data_julgamento_max,
                               orgao_principal, relator_principal, classe, url)
   └── "principal" = documento com tipo ACÓRDÃO mais recente; fallback SENTENÇA

3. Carregar STJ
   └── DuckDB: ler `stj-acordaos-dedup-YYYYMMDD.parquet`
   └── JOIN por numeroProcesso normalizado

4. Full outer join dos três conjuntos por nr_processo
   └── DuckDB: FULL OUTER JOIN em memória (~segundos para 100k processos)

5. Calcular fontes[] e n_fontes

6. Escrever `processos_unificados.parquet` + `processo_documentos.parquet`
   └── Upload para IA no item `causaganha-dashboard`

7. Atualizar cache do dashboard
   └── stj_render_queries.py e render_queries.py já lêem o parquet
```

Frequência: rodar após qualquer ciclo de ingestão de qualquer uma das três
fontes (DJEN diário, JURIS mensal, STJ mensal).

### 4.2 Complexidade e escala

| Conjunto | Processos únicos estimados | Cardinalidade média |
|---|---|---|
| DJEN | ~500k | 3 publicações/processo |
| TJRO JURIS | ~100k | 2 documentos/processo |
| STJ | ~50k | 1 espelho/processo (deduplicado) |
| **União** | **~550k** | — |

Full outer join de 550k chaves em DuckDB em memória: < 30 segundos.

## 5. Query contracts

### 5.1 `processo_detalhe.qmd`

Consulta parametrizada por `nr_processo`:

```sql
SELECT *
FROM processos_unificados
WHERE nr_processo = ?
```

Output: objeto JSON único com todos os campos da tabela.

### 5.2 `processos_multi_fonte.qmd`

Processos presentes em mais de uma fonte (os mais ricos para o dashboard):

```sql
SELECT nr_processo, nr_processo_mascara, n_fontes, fontes,
       djen_n_publicacoes, juris_n_documentos, stj_tema
FROM processos_unificados
WHERE n_fontes >= 2
ORDER BY n_fontes DESC, djen_ultima_pub DESC
LIMIT 500
```

### 5.3 `processo_documentos.qmd`

Todos os documentos de um processo por fonte:

```sql
SELECT fonte, tipo, data, resumo, url
FROM processo_documentos
WHERE nr_processo = ?
ORDER BY data DESC
```

## 6. UI — página `/processo/{cnj}`

### 6.1 URL canônica

```
/processo/70309694720248220001
/processo/7030969-47.2024.8.22.0001   (redireciona para a forma sem máscara)
```

### 6.2 Layout da página

```
┌─────────────────────────────────────────────────────────┐
│  7030969-47.2024.8.22.0001                              │
│  APELAÇÃO CÍVEL · TJRO · 2ª Câmara Cível               │
│  ● DJEN  ● JURIS  ● STJ                                 │
├──────────────┬──────────────┬───────────────────────────┤
│  DJEN        │  JURIS       │  STJ                      │
│  3 pub.      │  2 docs.     │  Tema 1234                │
│  2024-03-15  │  Acórdão     │  Tese: "..."              │
│  …           │  Relator: X  │  Rel.: Min. Y             │
│  [ver mais]  │  [integra]   │  [espelho completo]       │
└──────────────┴──────────────┴───────────────────────────┘

Linha do tempo:
  2024-01-10 DJEN pub. (caderno 001)
  2024-02-20 JURIS acórdão julgado
  2024-03-15 DJEN pub. (caderno 037)
  2025-06-01 STJ decisão (tema 1234)
```

### 6.3 Busca por CNJ

Adicionar `nr_processo` como parâmetro de busca global:

```
/search?q=7030969-47.2024.8.22.0001   →   redireciona para /processo/...
```

O campo de busca já aceita `numeroProcesso` (`web/src/lib/searchQueryString.ts`
linha existente) — estender para aceitar CNJ mascarado e normalizar antes do
redirect.

## 7. Decisões de design

### 7.1 Nr. CNJ como chave, não FK entre sistemas

Os IDs internos de cada fonte (`id_processo_documento` no JURIS, `id` no STJ)
não têm correspondência entre si. O único elo confiável é o número CNJ. Usar
FK interna exigiria um sistema de identidade centralizado — desnecessário
quando o CNJ já é o identificador judicial canônico.

### 7.2 `processos_unificados` é uma view materializada, não uma tabela mestre

Ela é **derivada** das três fontes a cada ciclo de reconciliação, nunca
editada manualmente. Se uma fonte corrigir um dado, a reconciliação seguinte
reflete a correção automaticamente.

### 7.3 Linha do tempo unificada via `processo_documentos`

Manter `processos_unificados` "flat" (uma linha por processo) e
`processo_documentos` para os eventos individuais separa dois níveis de
consulta: resumo rápido (landing page, listas) vs. detalhe completo
(página do processo).

### 7.4 Processos com número CNJ inválido ficam nas fontes originais

DJEN às vezes publica intimações sem número de processo (publicações
administrativas). STJ pode ter registros históricos com numeração pré-CNJ.
Esses registros permanecem nas tabelas de origem e são excluídos do join
sem erro.

### 7.5 STJ pode ter processos de outros tribunais

O STJ recebe recursos de todo o Brasil. `stj_id` pode cruzar com DJEN de
tribunais além do TJRO. A coluna `djen_tribunais[]` captura todos os tribunais
onde o processo apareceu no DJEN — o join é por CNJ, não filtrado por TJRO.

## 8. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Número CNJ com formatação divergente entre fontes | `normalizar_cnj()` centralizado; testes com amostras de cada fonte |
| STJ usa número pré-CNJ (antes de 2010) | Registros com < 20 dígitos ficam nas tabelas de origem; não bloqueiam o join |
| JURIS indexa processos de 1º e 2º grau com o mesmo nr_processo mas IDs distintos | `processo_documentos` preserva todos; `processos_unificados` agrega (n_documentos, tipos[]) |
| Reconciliação demora com 550k processos | DuckDB in-process; join em memória < 30s; rodar em background após ingestão |
| Parquet de `processos_unificados` fica grande | ~550k linhas × ~2KB/linha ≈ 1.1GB não comprimido → ~100MB com ZSTD; gerenciável |

## 9. Fora de escopo

- Reconciliação com outros tribunais além do TJRO no JURIS.
- Deduplicação de processos que migraram de número (renumeração CNJ histórica).
- Interface de edição ou correção manual de vínculos.
- Busca full-text por conteúdo da decisão na página de processo (RFC 0004
  habilita isso via embeddings; a UI fica para RFC subsequente).

## 10. Critérios de aceitação

- [ ] `normalizar_cnj()` é a única função de normalização no codebase; todas
  as fontes a usam.
- [ ] `reconcile_processos.py` produz `processos_unificados.parquet` sem erro
  com dados reais das três fontes.
- [ ] Nenhum `nr_processo` duplicado em `processos_unificados`.
- [ ] `n_fontes` reflete corretamente quantas fontes contribuíram para cada
  linha.
- [ ] Página `/processo/{cnj}` carrega e exibe dados das fontes presentes.
- [ ] Busca por CNJ mascarado redireciona corretamente para a página de detalhe.
- [ ] `uv run ruff check` e `uv run pytest -q` passam.

## 11. Referências

- RFC 0002: `docs/rfc/0002-stj-acordaos-dataset.md`
- RFC 0003: `docs/rfc/0003-tjro-juris-scraping.md`
- RFC 0004: `docs/rfc/0004-embeddings-juris-stj.md`
- Schema DJEN: `src/causaganha/storage/djen_schema.py`
- Consolidação: `src/causaganha/consolidate/transforms.py`
- Normalização CNJ existente: `.claude/skills/juris-tjro/scripts/juris.py:96–105`
- Query contracts: `web/src/queries/README.md`
- Busca por processo: `web/src/lib/searchQueryString.ts`
