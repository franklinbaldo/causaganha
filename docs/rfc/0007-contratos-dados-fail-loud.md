# RFC 0007 — Contratos de dados fail-loud (.qmd validados no PR, deploy estrito)

- **Status:** Proposto (implementação neste PR)
- **Data:** 2026-07-07
- **Base:** `docs/planning/oportunidades-melhoria-2026-07.md` §3

## 1. Problema

O caminho de dados do dashboard tem três falhas silenciosas encadeadas:

1. Os contratos `.qmd` (`web/src/queries/*.qmd`) só são executados no `deploy-web.yml`;
   o job `web` do CI de PR stuba `web/public/data/*.json`. Um `.qmd` com SQL quebrado
   passa verde no PR e só falha (ou nem falha) após o merge.
2. `scripts/render_queries.py` faz `continue` silencioso quando falta view/parquet
   (`CatalogException`) — o JSON simplesmente não é gerado.
3. As páginas degradam para vazio (`readJson` → `null` → `EmptyState`). Modo de falha
   real em produção: **seção vazia publicada sem ninguém alertado**.

## 2. Proposta

### 2.1 `render_queries.py --check` (validação estática, roda em PR)

Novo modo que, sem rede e sem manifest real:

- parseia o frontmatter de todos os `.qmd` (campos obrigatórios `output`, `format`;
  `format ∈ {array, object}`; `output` começa com `/data/`);
- valida o SQL de cada bloco com `duckdb` contra um **schema sintético** (mesmas
  colunas/tipos do manifest e das views que o render registra), pegando erro de sintaxe,
  coluna inexistente e referência a view não registrada;
- falha com exit code ≠ 0 listando cada `.qmd` inválido.

CI: novo passo no job `web` (ou `lint`) de `test.yml`: `uv run python
scripts/render_queries.py --check`.

### 2.2 Modo estrito no deploy (`--strict`)

- O conjunto esperado de outputs é derivado dos próprios `.qmd` (todo contrato declarado
  deve produzir seu JSON).
- Contratos que dependem de fontes **opcionais** (parquets que podem legitimamente não
  existir ainda, ex.: `lawyer_ratings`, `stj_*`, `juris_*`) declaram
  `optional: true` no frontmatter.
- Em `--strict` (usado em `deploy-web.yml`): output obrigatório ausente → **falha o
  build**; output opcional ausente → warning explícito no log (nunca `continue` mudo).

### 2.3 Sem mudança de contrato para o frontend

Os `.qmd` continuam a fonte da verdade; `format`/`output` inalterados. A validação Zod no
lado do site é escopo do RFC 0009.

## 3. Critérios de aceitação

- Quebrar deliberadamente um `.qmd` (coluna inexistente) → `--check` falha localmente e
  no CI de PR.
- Rodar render sem um parquet opcional → warning nominal no log, build segue; sem um
  obrigatório → exit ≠ 0.
- `deploy-web.yml` usa `--strict`; `test.yml` ganha o passo `--check`.
- Testes unitários para: parse de frontmatter (incl. `optional`), detecção de SQL
  inválido, classificação obrigatório/opcional.

## 4. Riscos

Falso positivo do `--check` se o schema sintético divergir do real → manter o schema
sintético gerado a partir da mesma definição usada pelo render (única fonte), não copiado
à mão.
