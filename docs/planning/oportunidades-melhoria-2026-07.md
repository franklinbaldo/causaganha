# Oportunidades de melhoria — análise a partir de primeiros princípios

- **Data:** 2026-07-07
- **Método:** auditoria completa do repositório (backend, CI/workflows, scripts, frontend),
  suíte de testes executada (302 pass / 1 skip), ruff limpo.
- **Status:** diagnóstico + priorização. Nenhuma mudança de comportamento neste PR.

---

## 0. Primeiros princípios

O propósito do projeto é: **(a)** arquivar comunicações judiciais (DJEN e afins) no
Internet Archive de forma completa e verificável, e **(b)** servir um dashboard público
confiável sobre esse acervo. Disso derivam os princípios usados para julgar o estado atual:

| # | Princípio | Pergunta-teste |
|---|---|---|
| P1 | **Uma fonte da verdade** — dado derivado é função pura e reproduzível da fonte | Posso apagar o derivado e regenerá-lo idêntico? |
| P2 | **Todo código tem custo de carregamento** — código que não roda em produção precisa justificar sua existência | Quem invoca isto? |
| P3 | **Falhar cedo e alto** — erro detectado no PR custa 10× menos que no deploy, 100× menos que em produção silenciosa | Onde este erro seria pego? |
| P4 | **Teste protege o que roda** — cobertura vale pelo risco que remove, não pelo número | O código novo em produção tem testes? |
| P5 | **CI deve espelhar produção** — um CI verde que exercita outra coisa dá falsa confiança | O que o CI valida é o que o deploy roda? |

O placar resumido: o núcleo (`src/djen_backup`, 3,7K linhas) é saudável, testado e é o único
código amarrado à automação. Em volta dele acumulou-se um custo de carregamento
desproporcional: **~14K+ linhas mortas em `src/causaganha`**, **15 scripts órfãos**,
**5 workflows com triggers apontando para branches que não existem**, **6 dependências
pesadas removíveis**, e uma migração de fonte-da-verdade **parada na Fase 1 de 3**.

---

## 1. Terminar a migração do manifesto (Fases 2–3) — P1, prioridade máxima

`docs/planning/manifest-source-of-truth.md` (decisão de 2026-06-01) já diagnosticou o
problema central: o Parquet derivado é *mais correto* que o CSV "canônico" (~79K linhas
legadas erradas). A Fase 1 (write-back de compactação) foi implementada
(`scripts/manifest_writeback.py`, `render_manifest_parquet.py`). Mas:

- **Fase 2 pendente:** o engine (`src/djen_backup/manifest.py` — `to_csv`/persist) ainda
  **reescreve o CSV inteiro** em vez de emitir segmentos de log imutáveis. Enquanto isso,
  a deriva pode voltar: qualquer run longo do engine re-serializa estado velho por cima.
- **Fase 3 pendente:** 16 arquivos em `src/` + `scripts/` e **7 workflows** ainda referenciam
  `sync-manifest.csv` diretamente.

**Por que é a melhor oportunidade:** é o único item que ameaça a *integridade do dataset*,
que é o produto. Tudo o mais é custo; isto é risco. O plano já existe e está faseado —
falta executar.

**Ação:** implementar Fase 2 (writers emitem segmentos `manifest-log/`), depois Fase 3
(aposentar o CSV como fonte; leitores só no Parquet).

---

## 2. A grande poda — P2

Auditoria de alcance real (entry points × workflows × imports):

- **Único entry point em produção:** `djen-backup` (via `collect-zips.yml`,
  `upload-backlog.yml`). O CLI monolítico `causaganha` (~1.500 linhas em
  `src/causaganha/cli/`) **não é invocado por nenhum workflow** — e é o único caminho que
  mantém vivos `pipeline/{analyze,collect,score,export_orchestrator,ia_download,
  ia_parquet_uploader,parquet_export,repositories}`, `scoring/openskill`,
  `storage/{repositories,migrations}`, `catalog/creator`, `archival/cold_storage`,
  `compliance/report` e `analysis/{ground_truth,vector_store}`.
- **A fatia viva de `src/causaganha` é fina:** `config`, `pipeline/ia_s3`,
  `storage/{connection,djen_schema}`, o núcleo de `consolidate/` (7 módulos) e,
  marginalmente, `analysis/{keyword_classifier,llm_analyzer,models}` (smoke `--mock`).
- **Órfãos absolutos** (nada importa, nem testes): `analysis/entity_ruler.py`,
  `analysis/ner_pipeline.py`, `analysis/document_markup.py`; quase-órfãos (só o próprio
  teste): `analysis/api_embedder.py`, `analysis/text_truncate.py`.
- **Caminho aspiracional duplicado:** `consolidate/{cli,__main__,candidates,checkpoint,
  exporter}` foi substituído em runtime por `scripts/pipeline/consolidate.py`.
- **Dependências removíveis hoje** (únicos importadores são código morto): `spacy`,
  `accelerate`, `transformers`, `boto3`, `fpdf`, `lancedb`. Bônus: portar
  `scripts/generate_catalog.py` de `aiohttp` para `httpx` elimina o cliente HTTP duplicado;
  `dbt-duckdb` (dev) não tem projeto dbt no repo.
- **Scripts:** 82 arquivos / 22K linhas em `scripts/`; **15 são órfãos totais** (zero
  referências em código, workflow ou doc) — ex.: `analyze_pipeline_performance.py`,
  `probe_tribunal_start_dates.py`, `validate_system_health.py`, `laptop_service.py`,
  `monitor_github_backfill.py`.
- **Lixo versionado na raiz:** `server.log`, `dev_output.log`, `run_stats.json`,
  `ia_data.json` estão em `git ls-files`.
- **Workflows com trigger morto:** `manifest-writeback.yml`, `roundtrip-check.yml`,
  `bootstrap-corpus.yml` (push → `claude/epic-clarke-9uaaQ`, branch inexistente),
  `backfill-probe.yml` (idem), `recover-manifest.yml` (one-off autodeclarado).
- **Referências quebradas:** `analysis/benchmark_store.py:15` cita
  `scripts/compact_benchmark.py` (não existe); RFCs 0003/0005 citam `scripts/juris.py`
  (não existe).

**Por que importa:** cada linha morta é superfície de manutenção, de review de segurança,
de resolução de dependência (o `uv sync` instala 251 pacotes) e de confusão para quem chega.
A poda é a melhoria de maior razão benefício/custo do repositório: remove ~60–70% do volume
de `src/causaganha` + `scripts/` sem tocar em nada que roda.

**Ação sugerida (em PRs pequenos e reversíveis):** (1) deletar logs/artefatos da raiz e
gitignorar; (2) deletar os 15 scripts órfãos e os 5 órfãos de `analysis/`; (3) remover
triggers de branch morta dos workflows; (4) decidir o destino do CLI `causaganha` — ou vira
automação real, ou sai com sua cauda inteira; (5) enxugar `pyproject.toml`. Se parte do
código "experimental" (RAG/embeddings/ML) tem futuro planejado (RFC 0004), movê-lo para um
pacote/branch de experimentos explícito em vez de conviver com produção.

---

## 3. Falhar no PR, não no deploy — P3/P5

O caminho de dados do dashboard tem três falhas silenciosas encadeadas:

1. **Contratos `.qmd` nunca rodam em PR.** O job `web` do CI stuba
   `web/public/data/*.json`; `render_queries.py` só executa no `deploy-web.yml`. Um `.qmd`
   quebrado passa verde no PR e explode (ou pior, não explode) após o merge.
2. **`render_queries.py` faz SKIP silencioso** quando falta view/parquet — o JSON
   simplesmente não é gerado.
3. **As páginas degradam para vazio** (`readJson` → `null` → `EmptyState`). Resultado
   possível: dashboard publicado com seções vazias e ninguém alertado — o "drift" real é
   *ausência silenciosa de dados*, não dado desatualizado.

**Ação:** (a) rodar `render_queries.py --check` no CI de PR (valida sintaxe/SQL dos 16
`.qmd` contra um manifest de amostra ou o real); (b) modo estrito no deploy: lista de
outputs esperados, build falha se algum JSON esperado não foi gerado; (c) opcional, validar
os JSONs gerados com Zod no build do Astro (Zod já é dependência do web).

---

## 4. Testar o que acabou de entrar em produção — P4

- **`src/stj_acordaos` (5 módulos) e `src/tjro_juris` (6 módulos): zero testes.** São as
  implementações recém-mescladas dos RFCs 0002/0003 — exatamente o código com maior chance
  de bug latente. Prioridade: `dedup`, `manifest` e parsing do `client` (puros, fáceis de
  testar; o padrão já existe em `tests/djen_backup/`).
- Lacunas no núcleo: `djen_backup/{retry,probe,credentials,tribunais}.py` sem teste direto
  — `retry.py` em particular protege todo o I/O.
- **Lacuna operacional correlata:** `stj-acordaos` e `tjro-juris` não são invocados por
  nenhum workflow. Sem cron, esses datasets **não crescem** — os RFCs estão implementados
  mas não operacionalizados. Decidir: agendar (como `collect-zips`) ou documentar como
  execução manual deliberada.

---

## 5. Coerência da camada de dados do frontend

- **`web/src/lib/queryData.ts` é código morto com bug:** nenhum componente o importa, e ele
  usa caminho absoluto `/data/...` ignorando `base: '/causaganha'` (quebraria em Pages).
  Deletar antes que alguém o reuse.
- **Três sistemas de loading coexistem** (`readJson`, `fetchData`/`buildTimeData`, e o morto
  `queryData`), com tipos independentes e `readJson<any>` inline em `advogados.astro` e
  `comparador.astro`. Consolidar em um módulo único com tipos derivados dos 16 contratos
  `.qmd` (hoje só 6 têm tipo).
- Menores: chave `prefetch` duplicada em `astro.config.mjs`; padrões de
  tabela/`auto-grid` re-implementados por página (extrair componente de tabela); rotas
  `advogados/[tribunal]` geram **zero páginas** se `cache/backfill.json` faltar no build
  (mesma classe de falha silenciosa do item 3).

---

## 6. Itens menores (colher quando passar perto)

| Item | Evidência |
|---|---|
| Matriz de teste degenerada `tribunal: [tjro]` no CI | `.github/workflows/test.yml` |
| `ia-practicality-probe` roda toda segunda para sempre — ainda gera decisão? | cron semanal ativo |
| `data/` com 9,2 MB / 236 arquivos versionados (benchmark + segmenter samples) — usados, mas candidatos a item no IA em vez de git | `data/benchmark/`, `data/segmenter_samples/` |
| `permissions: contents: write` amplo no CI de PR | `test.yml` |
| Corrigir referências quebradas em docs/código (`compact_benchmark.py`, `scripts/juris.py`) | §2 |

---

## Ordem recomendada

1. **Manifesto Fases 2–3** (integridade do produto; plano pronto).
2. **Poda** (código morto, scripts, deps, workflows, lixo versionado) — em PRs pequenos.
3. **`.qmd` no CI de PR + modo estrito no deploy** (protege o dashboard público).
4. **Testes stj/tjro + decisão de operacionalização** (cron ou manual documentado).
5. **Limpeza da camada de dados do web** (deletar `queryData.ts`, unificar loaders).

Os itens 2, 3 e 5 são mecânicos e de baixo risco; o item 1 é o único com sequenciamento
operacional delicado (parar engine → write-back → religar, já documentado no plano).
