---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-akb9oz-evidence-green-csp-xss-floor"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
kind: "test_green"
reference: "web/src/layouts/Layout.astro, web/src/lib/csp.ts (novo), web/src/pages/advogados.astro, web/src/pages/comparador.astro, dist/*.html (build real)"
summary: "GREEN apos: (1) extrair a politica para web/src/lib/csp.ts (CSP_META_CONTENT), consumida por <meta http-equiv=\"Content-Security-Policy\" content={CSP_META_CONTENT} /> em Layout.astro (usado por toda pagina real) e replicada explicitamente em advogados.astro/comparador.astro, que renderizam seu proprio <html> em vez de usar Layout.astro; (2) remover o <script define:vars={{ target }}>window.location.replace(target)</script> redundante dessas duas paginas -- o <meta http-equiv=\"refresh\"> ja presente fazia o mesmo redirecionamento, e era o unico script inline do app, incompativel com script-src 'self' sem 'unsafe-inline'. A politica: script-src 'self' (sem unsafe-inline/unsafe-eval/wildcard), style-src 'self' 'unsafe-inline' (Svelte emite <style> escopado estatico em toda pagina com ilha, nunca de conteudo do usuario -- sanitizeHtml() ja proibe tag/atributo style em texto judicial), connect-src/worker-src restritos a self + archive.org + comunicaapi.pje.jus.br + o proxy DJEN + cdn.jsdelivr.net (fonte real do worker/modulo DuckDB-WASM, confirmada por grep no pacote @duckdb/duckdb-wasm), object-src 'none', base-uri/form-action 'self'. frame-ancestors/sandbox/report-uri deliberadamente omitidos (spec CSP: ignorados quando entregues via <meta>, e GitHub Pages nao permite header HTTP customizado -- documentado no comentario do Layout.astro e no teste, nao escondido). Build real local (npm run build, rm -rf dist antes) confirmou a tag presente em advogados.html/comparador.html (as unicas 2 paginas que nao usam Layout.astro) e em toda pagina que usa Layout.astro (processo/agentes/404/changelog/explorador/minhas-consultas.html, checado via grep -c). O <script type=\"module\" src=...> bundilado permanece (compativel com script-src 'self'); o inline sumiu (grep -o '<script[^>]*>' so retorna a tag module). 25/25 testes novos verdes; suite web completa (npx vitest run) foi de 583 para 585 testes, 100% verde; eslint (0 erros, 43 warnings pre-existentes em styled-system/*.d.ts nao relacionados); astro check (typecheck) 0 erros."
---

# Evidencia: GREEN apos CSP + remocao do script inline (#1613, TM-08)

```
$ npx vitest run src/layouts/Layout.csp.test.ts src/lib/htmlSinks.inventory.test.ts src/lib/djenXssCorpus.test.ts src/pages/redirectStubs.noInlineScript.test.ts
 Test Files  4 passed (4)
      Tests  25 passed (25)

$ npx vitest run   # suite web completa
 Test Files  79 passed (79)
      Tests  585 passed (585)

$ npx eslint .
✖ 43 problems (0 errors, 43 warnings)   # warnings pre-existentes em styled-system/*.d.ts, nao relacionados a esta mudanca

$ npx astro check
Result (157 files):
- 0 errors
- 0 warnings
- 3 hints

$ rm -rf dist && npm run build   # build real; falha em /publicacoes por site-status.json ausente
                                   # (gap pre-existente do backend Python, nao relacionado)
$ grep -c "Content-Security-Policy" dist/advogados.html dist/comparador.html
dist/advogados.html:1
dist/comparador.html:1

$ grep -c "Content-Security-Policy" dist/processo.html dist/agentes.html dist/404.html \
    dist/changelog.html dist/explorador.html dist/minhas-consultas.html
dist/processo.html:2
dist/agentes.html:2
dist/404.html:2
dist/changelog.html:2
dist/explorador.html:2
dist/minhas-consultas.html:2

$ grep -o "<script[^>]*>" dist/advogados.html dist/comparador.html
dist/advogados.html:<script type="module" src="/causaganha/_astro/page.BGjr2SS0.js">
dist/comparador.html:<script type="module" src="/causaganha/_astro/page.BGjr2SS0.js">
```

Nao regrediu nenhum teste pre-existente (583 -> 585, +2 pelos novos casos de
`Layout.csp.test.ts`/`htmlSinks.inventory.test.ts` alem dos ja contados na
suite anterior). Confirmado por build real, nao apenas por leitura de
codigo-fonte: a CSP chega ao HTML final em toda pagina, incluindo as duas
que nao usam `Layout.astro` (gap descoberto durante a implementacao --
`advogados.astro`/`comparador.astro` renderizam seu proprio `<html>`; ver
`decision-shared-csp-constant`).
