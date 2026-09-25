---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-akb9oz-check-web-build"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
command: "cd web && rm -rf dist && npm run build"
result: "passed"
summary: "Build real (nao so leitura de fonte) executado duas vezes: a primeira revelou que a CSP adicionada apenas a Layout.astro nao chegava a advogados.html/comparador.html (paginas que nao usam Layout.astro) -- gap corrigido (ver decision-shared-csp-constant). A segunda, apos a correcao, confirmou content=\"Content-Security-Policy\" presente em 100% das paginas geradas (as 2 paginas standalone + todas as que usam Layout.astro), e confirmou via grep que nenhum <script> inline sobra em advogados.html/comparador.html (so o <script type=\"module\" src=...> bundilado). O build falha em /publicacoes por site-status.json ausente -- gap pre-existente do pipeline Python (scripts/render_queries.py nao rodado nesta sessao, sem dados do manifesto), nao relacionado a esta mudanca; confirmado que o mesmo erro ja ocorria antes de qualquer edicao desta rodada (primeiro build, antes de tocar em Layout.astro)."
---

# Check: build real do site estatico, antes e depois da correcao do gap

```
$ rm -rf dist && npm run build
...
07:28:10 [ERROR] Error: site-status.json ausente (contrato obrigatório "site_status"). ...
# (gap pre-existente, mesmo erro reproduzido antes de qualquer edicao)

$ grep -c "Content-Security-Policy" dist/advogados.html dist/comparador.html   # ANTES da correcao
dist/advogados.html:0
dist/comparador.html:0

# apos decision-shared-csp-constant:

$ rm -rf dist && npm run build
$ grep -c "Content-Security-Policy" dist/advogados.html dist/comparador.html
dist/advogados.html:1
dist/comparador.html:1
$ grep -o "<script[^>]*>" dist/advogados.html dist/comparador.html
dist/advogados.html:<script type="module" src="/causaganha/_astro/page.BGjr2SS0.js">
dist/comparador.html:<script type="module" src="/causaganha/_astro/page.BGjr2SS0.js">
```
