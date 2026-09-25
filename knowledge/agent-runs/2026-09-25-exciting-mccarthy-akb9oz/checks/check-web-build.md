---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-akb9oz-check-web-build"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
command: "cd web && rm -rf dist && npm run build (repetido varias vezes ao longo da rodada, cada vez apos uma mudanca real)"
result: "passed"
summary: "Build real (nao so leitura de fonte) executado repetidamente durante a rodada, cada vez revelando um gap novo que nenhum teste Vitest cobria: (1) primeiro build mostrou que a CSP adicionada apenas a Layout.astro nao chegava a advogados.html/comparador.html (paginas que nao usam Layout.astro) -- corrigido (decision-shared-csp-constant); (2) apos a correcao, build confirmou content=\"Content-Security-Policy\" presente em 100% das paginas geradas e nenhum <script> inline sobrando em advogados.html/comparador.html; (3) apos wire do npm postbuild (injectCspHashes.mjs), build final confirmou 'injectCspHashes: patched CSP script-src hashes into 103/111 page(s)' e os hashes gravados em dist/processo.html batem exatamente com os 3 hashes que um Chromium real reportou como bloqueados antes do fix (ver evidence-fix-csp-blocks-astro-hydration). O build sempre falha em /publicacoes por site-status.json ausente -- gap pre-existente do pipeline Python (scripts/render_queries.py nao rodado nesta sessao), nao relacionado a esta mudanca; confirmado que o mesmo erro ja ocorria antes de qualquer edicao desta rodada. Quando fixtures sinteticas identicas as do workflow de CI (site-status.json etc.) sao fornecidas, o build completa as 111 paginas sem nenhum erro."
---

# Check: build real do site estatico, repetido a cada correcao

```
$ rm -rf dist && npm run build   # ANTES da correcao do gap advogados/comparador
$ grep -c "Content-Security-Policy" dist/advogados.html dist/comparador.html
dist/advogados.html:0
dist/comparador.html:0

# apos decision-shared-csp-constant:
$ rm -rf dist && npm run build
$ grep -c "Content-Security-Policy" dist/advogados.html dist/comparador.html
dist/advogados.html:1
dist/comparador.html:1

# apos decision-csp-hash-not-unsafe-inline (postbuild wired):
$ rm -rf dist && npm run build
...
07:49:50/etc [build] 111 page(s) built in Xs
[build] Complete!

> web@0.0.0 postbuild
> node scripts/injectCspHashes.mjs

injectCspHashes: patched CSP script-src hashes into 103/111 page(s).

$ grep -o "script-src[^;]*;" dist/processo.html
script-src 'self' 'sha256-Ya0pUYrC7nM5Cn/056TyVuEiz6dFGrzmkWzgON0pF0U='
  'sha256-eIXWvAmxkr251LJZkjniEK5LcPF3NkapbJepohwYRIc='
  'sha256-ywDn4AkgLzJyrJIM2y/daMBkO4v1+WOHLIVFHbnbfH0=';
```
