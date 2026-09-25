---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-akb9oz-evidence-ci-fix-redirect-stub-test-as-astro-page"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
kind: "ci"
reference: "PR #1628, check run compare-product-surfaces (job 107989132075, run 36109387182)"
summary: "CI de PR #1628 falhou no job compare-product-surfaces com 'Caught error rendering /redirectStubs.noInlineScript.test: TypeError: Cannot read properties of undefined (reading config)'. Causa raiz: web/src/pages/redirectStubs.noInlineScript.test.ts (arquivo de teste desta rodada) vive dentro de web/src/pages/, o diretorio de roteamento por arquivo do Astro -- qualquer arquivo ali sem prefixo _ vira uma rota real que o astro build tenta renderizar como pagina. O repositorio ja tinha 2 precedentes desse padrao (src/pages/_index.agentsCta.test.ts, src/pages/publicacoes/_index.order.test.ts), ambos com o prefixo _ que a propria convencao do Astro exclui do roteamento -- meu arquivo novo nao seguiu essa convencao. Build local (npm run build, sem fixtures de dados) nunca teria revelado o bug porque o build local sempre abortava antes em /publicacoes (site-status.json ausente, gap pre-existente do pipeline Python) -- 'redirectStubs...' vem depois de 'publicacoes' em ordem alfabetica. So apareceu no CI porque o job compare-product-surfaces cria fixtures sinteticas de site-status.json/etc. (.github/workflows/cobogo-core-adoption-capture.yml) e por isso chega mais longe no build. Corrigido com git mv para src/pages/_redirectStubs.noInlineScript.test.ts (mesmo prefixo dos 2 precedentes). Reproduzido localmente com as mesmas fixtures sinteticas do workflow (site-status.json etc. em web/public/data/): build completo (111 paginas) sem nenhum erro de renderizacao, nenhum arquivo _redirectStubs* em dist/, CSP presente em todas as paginas verificadas. Suite Vitest completa re-rodada apos o rename: 79/79 arquivos, 585/585 testes verdes (um primeiro re-run mostrou 1 falha isolada em svelteA11y.contract.test.ts, arquivo pre-existente nao tocado por esta rodada; confirmado flake por um segundo re-run 100% limpo, sem relacao com a mudanca)."
---

# Evidencia: CI vermelho por arquivo de teste dentro de src/pages/ (roteamento Astro), corrigido

```
$ mcp__github__get_job_logs(job_id=107989132075, run_id=36109387182, failed_only=true)
...
07:47:41 [ERROR] TypeError: Cannot read properties of undefined (reading 'config')
07:47:41 [ERROR] [build] Caught error rendering /redirectStubs.noInlineScript.test: TypeError: Cannot read properties of undefined (reading 'config')
##[error]Process completed with exit code 1.
```

```
$ find web/src/pages -iname "*.test.ts"
src/pages/_index.agentsCta.test.ts          # precedente: prefixo _ (excluido do roteamento Astro)
src/pages/redirectStubs.noInlineScript.test.ts   # meu arquivo, SEM prefixo -- bug
src/pages/publicacoes/_index.order.test.ts  # precedente: prefixo _

$ git mv src/pages/redirectStubs.noInlineScript.test.ts src/pages/_redirectStubs.noInlineScript.test.ts
```

Build local reproduzindo as fixtures sinteticas do workflow
`cobogo-core-adoption-capture.yml` (site-status.json etc. em
`web/public/data/`), antes inacessivel localmente porque o build sempre
abortava antes em `/publicacoes`:

```
$ rm -rf dist && npm run build
...
07:49:50   ├─ /index.html (+4ms)
07:49:50 ✓ Completed in 487ms.
07:49:50 [build] 111 page(s) built in 6.80s
07:49:50 [build] Complete!

$ find dist -iname "*redirectStubs*" -o -iname "*noInlineScript*"
# (vazio)

$ grep -c "Content-Security-Policy" dist/advogados.html dist/comparador.html dist/stats.html dist/processo.html
dist/advogados.html:1
dist/comparador.html:1
dist/stats.html:2
dist/processo.html:2
```
