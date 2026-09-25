---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-akb9oz-evidence-red-csp-xss-floor"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
kind: "test_red"
reference: "web/src/layouts/Layout.csp.test.ts (novo, 8 testes), web/src/lib/htmlSinks.inventory.test.ts (novo), web/src/lib/djenXssCorpus.test.ts (novo)"
summary: "Os 3 arquivos de teste foram escritos primeiro contra o codigo de producao anterior (nenhuma CSP em Layout.astro). npx vitest run confirmou RED isolado exatamente ao gap que #1613 descreve: 8/8 testes de Layout.csp.test.ts falharam com 'No <meta http-equiv=\"Content-Security-Policy\"> tag found in Layout.astro' -- prova de que nenhuma forma de CSP existia antes desta mudanca. Os outros dois arquivos novos (htmlSinks.inventory.test.ts, djenXssCorpus.test.ts) ja passavam contra o codigo anterior -- nao sao RED no sentido de bug a corrigir, mas sim piso de regressao novo sobre comportamento correto ja existente (DOMPurify em sanitizeHtml() ja neutralizava o corpus XSS testado, e so 2 arquivos ja usavam {@html}) -- exatamente o 'gate automatizado' que a issue pede para travar contra regressao futura, nao para corrigir um bug presente."
---

# Evidencia: RED antes de adicionar a CSP (#1613, TM-08)

```
$ npx vitest run src/layouts/Layout.csp.test.ts src/lib/htmlSinks.inventory.test.ts src/lib/djenXssCorpus.test.ts

 FAIL  src/layouts/Layout.csp.test.ts > ... > declares a CSP meta tag in <head>
 FAIL  src/layouts/Layout.csp.test.ts > ... > script-src is self-only: no unsafe-inline, no unsafe-eval, no wildcard
 FAIL  src/layouts/Layout.csp.test.ts > ... > object-src is none (no plugins/legacy embeds)
 FAIL  src/layouts/Layout.csp.test.ts > ... > base-uri and form-action are locked to self
 FAIL  src/layouts/Layout.csp.test.ts > ... > connect-src is a closed allowlist covering every host the app actually fetches
 FAIL  src/layouts/Layout.csp.test.ts > ... > worker-src allows only self, blob: (DuckDB-WASM fallback) and the jsDelivr CDN it loads from
 FAIL  src/layouts/Layout.csp.test.ts > ... > no directive contains a bare wildcard origin
 FAIL  src/layouts/Layout.csp.test.ts > ... > style-src stays self + unsafe-inline ...

Error: No <meta http-equiv="Content-Security-Policy"> tag found in Layout.astro

 Test Files  1 failed | 2 passed (3)
      Tests  8 failed | 13 passed (21)
```

Confirma que `Layout.astro` nao continha nenhuma forma de `<meta
http-equiv="Content-Security-Policy">` antes desta mudanca -- exatamente o
gap descrito pela linha TM-08 de `docs/SECURITY_THREAT_MODEL.md` ("Nao ha
CSP em Layout.astro").
