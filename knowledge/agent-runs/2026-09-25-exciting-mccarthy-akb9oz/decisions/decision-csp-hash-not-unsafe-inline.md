---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-akb9oz-decision-csp-hash-not-unsafe-inline"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
question: "compare-product-surfaces (real Playwright browser against a real build) revealed that Astro's own client-hydration runtime injects small inline <script> tags into every page with a hydrated island (astro-island bootstrap, astro:transitions ClientRouter), which script-src 'self' with no unsafe-inline blocks outright -- confirmed live: ProcessoLookup.svelte never hydrates, the CNJ validation message never appears. How to reconcile a strict script-src with a framework that requires inline scripts to function?"
choice: "Build-time SHA-256 hash allowlisting: a new postbuild script (web/scripts/injectCspHashes.mjs) scans every dist/**/*.html after astro build, computes the sha256-base64 hash of each inline <script> (no src) tag's exact content, and rewrites that page's CSP script-src to add 'sha256-<hash>' for each one found. Never added 'unsafe-inline' to script-src."
rationale: "'unsafe-inline' would defeat the entire purpose of #1613 -- it is the exact XSS vector the issue exists to close, and DOMPurify's own sanitizeHtml() output would then run under a script-src that permits any inline script, including one smuggled through a future sanitizer bypass. A CSP nonce doesn't work for a static site: nonces must be unique per response to provide real protection, but this is a pre-rendered HTML file served identically to every visitor forever (until the next deploy) -- a 'static nonce' is readable from the page source and provides no more protection than 'unsafe-inline' while looking more secure than it is. A hash allowlist is the correct mechanism for exactly this case (framework-injected, deterministic-per-build inline scripts) and is what serious static-site frameworks with CSP support (e.g. SvelteKit's built-in csp.mode='hash') do natively -- Astro has no such built-in, so it's implemented here as a small, independently unit-tested (RED/GREEN TDD, injectCspHashes.test.ts) postbuild step wired into package.json's npm lifecycle (postbuild runs automatically after every `npm run build`, in CI and locally, so it can never be forgotten or run out of sync with the actual build output). Verified live, not just by grep: a real headless Chromium loading dist/processo.html?cnj=123 under the exact CSP this PR ships refused all 3 inline scripts and never rendered the validation message before this fix; after wiring the postbuild step, the identical probe found the message. This was caught by CI's compare-product-surfaces job (the only check in the repo that exercises a real browser against the real built site) hanging/failing twice on this PR before being root-caused -- vitest, eslint and astro check all stayed green throughout because none of them load a real page in a real browser under the actual CSP, which is precisely the gap a static <meta> CSP creates: it is easy to ship a policy that is syntactically present and passes every source-level test while silently breaking the product for every real visitor."
---

# Decisao: hash allowlisting via postbuild, nunca unsafe-inline

Descoberto por CI real (compare-product-surfaces), nao por nenhum teste
Vitest: a CSP `script-src 'self'` sem `unsafe-inline` bloqueia os scripts
inline que o proprio Astro injeta para hidratar ilhas Svelte -- confirmado
ao vivo com Chromium real, `ProcessoLookup.svelte` nunca hidratava sob a
politica original. Resolvido com um passo `postbuild`
(`web/scripts/injectCspHashes.mjs`, TDD completo) que calcula o hash
sha256 de cada `<script>` inline do build real e o adiciona ao
`script-src` de cada pagina -- nunca com `unsafe-inline`, que reabriria
exatamente a superficie de XSS que `#1613` fecha. Ver
`evidence-fix-csp-blocks-astro-hydration` para a reproducao completa.
