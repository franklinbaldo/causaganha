# RFC 0009 — Unificação da camada de dados do frontend

- **Status:** Proposto (implementação neste PR)
- **Data:** 2026-07-07
- **Base:** `docs/planning/oportunidades-melhoria-2026-07.md` §5; complementa RFC 0007

## 1. Problema

Três sistemas de carregamento de dados coexistem em `web/src/lib`:

1. **`queryData.ts`** — morto (nenhum importador) e **incorreto**: usa `/data/...`
   absoluto, ignorando `base: '/causaganha'` do `astro.config.mjs`. Risco de reuso.
2. **`readJson.ts`** — build-time (`fs.readFileSync`), retorna `null` em falha; usado
   pelas páginas com `readJson<any>` inline (`advogados.astro`, `comparador.astro`).
3. **`fetchData.ts`/`buildTimeData.ts`** — build + cliente, resolve o base corretamente.

Dos 16 contratos `.qmd`, só 6 têm tipo declarado; nenhum JSON é validado em runtime
apesar de Zod já ser dependência.

## 2. Proposta

1. **Deletar `queryData.ts`.**
2. **Módulo único `web/src/lib/data/`**: um arquivo `contracts.ts` com um schema Zod por
   contrato `.qmd` (16) + tipos inferidos (`z.infer`), e um loader único com dois modos —
   build-time (fs) e client-side (fetch com base resolvido) — substituindo
   `readJson`/`fetchData` gradualmente:
   - build-time: parse + validação Zod; dado inválido → **falha o build** (erro nominal
     com o nome do contrato), dado ausente → `null` tipado (páginas mantêm EmptyState);
   - client-side: mesma validação, erro logado e tratado como ausência.
3. **Eliminar `readJson<any>`**: `advogados.astro`, `comparador.astro`, `stats.astro` e
   páginas de tribunal passam a importar os tipos dos contratos.
4. **Correções pontuais:** remover a chave `prefetch` duplicada em `astro.config.mjs`.

Fora de escopo: unificação visual/CSS (dois sistemas de tokens — decisão de design do
owner), componentes de tabela compartilhados (limpeza incremental futura).

## 3. Critérios de aceitação

- `queryData.ts` removido; `npm run build`, `npm test`, `npm run lint` e
  `npm run typecheck` verdes em `web/`.
- 16 contratos com schema Zod; zero `readJson<any>` restante (grep).
- JSON deliberadamente malformado em `web/public/data/` → build falha com mensagem
  apontando o contrato (verificado em teste).

## 4. Riscos

Schemas Zod mais estritos que os dados reais (ex.: campo nulo inesperado) quebrariam o
deploy → schemas iniciais tolerantes (`.nullable()`/`.optional()` onde o SQL permite
NULL), endurecendo depois com dados observados.
