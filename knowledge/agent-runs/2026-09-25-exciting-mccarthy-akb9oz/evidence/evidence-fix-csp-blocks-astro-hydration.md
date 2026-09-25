---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-akb9oz-evidence-fix-csp-blocks-astro-hydration"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
kind: "runtime"
reference: "PR #1628, check run compare-product-surfaces (job 107999622752, run 36112722861); web/scripts/injectCspHashes.mjs; web/scripts/injectCspHashes.test.ts"
summary: "Apos o fix de evidence-ci-fix-a11y-audit-csp-inline-script (commit ff70c77), compare-product-surfaces ainda ficou cancelled: passo 9 (audit de acessibilidade) passou (14s), mas o passo 10 (Capture desktop and mobile product surfaces, roda com if: always()) travou de novo ate estourar o timeout de 20min -- comparado com 200+ execucoes historicas do mesmo workflow, todas concluidas em ~3min, confirmando que o travamento e causado por esta PR, nao um flake pre-existente. Diagnostico: capture_invalid_process() espera pelo texto 'CNJ inválido' em processo.html?cnj=123 sem timeout explicito. Reproduzido ao vivo (Chromium real, build real desta PR, mesmas fixtures sinteticas do CI): page.goto succeeds (status 200) mas 3 mensagens de console 'Refused to execute inline script because it violates ... script-src 'self'' aparecem, e o texto nunca aparece (timeout apos 15s no probe local, contra timeout indefinido/20min no CLI real do CI). Causa raiz: Astro injeta 3 scripts inline (nao <script src=...>) em toda pagina com ilha hidratada -- o bootstrap astro-island e o runtime do ClientRouter (astro:transitions) que Layout.astro usa -- e a CSP desta PR (script-src 'self', sem unsafe-inline) os bloqueia integralmente, entao ProcessoLookup.svelte nunca hidrata e a validacao de CNJ nunca roda. Isso e uma quebra real de funcionalidade do produto em qualquer navegador real, nao so um problema de CI: nenhum teste Vitest/eslint/astro-check pegou porque nenhum deles carrega uma pagina real num browser real sob a CSP real. Corrigido com hash allowlisting em vez de unsafe-inline (ver decision-csp-hash-not-unsafe-inline): novo web/scripts/injectCspHashes.mjs, TDD completo (10 testes RED-then-GREEN em injectCspHashes.test.ts cobrindo calculo de hash, injecao idempotente no script-src, e rewrite do <meta> CSP num documento HTML completo), rodado como npm postbuild (automatico apos todo `npm run build`, local e em CI/deploy-web.yml, sem exigir nenhuma mudanca nos workflows). Apos o fix: build real, hashes das 3 tags inline efetivamente gravados no <meta> CSP de dist/processo.html (conferido por grep, batem exatamente com os 3 hashes que o Chromium reportou como bloqueados), e o mesmo probe ao vivo agora encontra 'CNJ inválido' apos hidratacao bem-sucedida. Suite Vitest completa (80 arquivos, 595 testes, +10 dos novos testes de injectCspHashes) e eslint/astro check 100% verdes."
---

# Evidencia: CSP bloqueava hidratacao real do Astro, corrigido com hash allowlist

Comparacao com o historico do workflow (nenhuma das ~200 execucoes
anteriores travou; as duas execucoes anteriores desta PR travaram no mesmo
ponto):

```
$ mcp__github__actions_list(method=list_workflow_runs, resource_id=cobogo-core-adoption-capture.yml)
run #415 (ff70c77, esta PR): cancelled, 08:24 -> 08:49 (~25min)
run #414 (2cd441f, esta PR): cancelled, 07:54 -> 08:19 (~25min)
run #412 (main):              success,   3min
run #410 (main):              success,   3min
run #408 (main):              success,   3min
... (todas as demais, success em ~3min)
```

Diagnostico ao vivo (build real desta PR, Chromium real,
`page.waitForSelector('text=CNJ inválido', {timeout: 15000})`):

```
goto http://127.0.0.1:4174/causaganha/processo.html?cnj=123
[console] error Refused to execute inline script because it violates the
following Content Security Policy directive: "script-src 'self'". ...
sha256-ywDn4AkgLzJyrJIM2y/daMBkO4v1+WOHLIVFHbnbfH0=...
[console] error Refused to execute inline script ... sha256-eIXWvAmxkr25...
[console] error Refused to execute inline script ... sha256-Ya0pUYrC7nM5...
status 200
TIMEOUT waiting for CNJ inválido: page.waitForSelector: Timeout 15000ms exceeded.
```

TDD do fix (`web/scripts/injectCspHashes.test.ts`, RED antes do modulo
existir -- `Failed to resolve import "./injectCspHashes.mjs"` -- GREEN apos
implementar `computeInlineScriptHashes`/`injectHashesIntoCsp`/`rewriteHtmlCsp`):

```
$ npx vitest run scripts/injectCspHashes.test.ts
Test Files  1 passed (1)
     Tests  10 passed (10)
```

Build real + verificacao dos hashes injetados + re-probe ao vivo:

```
$ rm -rf dist && npm run build
...
> web@0.0.0 postbuild
> node scripts/injectCspHashes.mjs
injectCspHashes: patched CSP script-src hashes into 103/111 page(s).

$ grep -o "script-src[^;]*;" dist/processo.html
script-src 'self' 'sha256-Ya0pUYrC7nM5Cn/056TyVuEiz6dFGrzmkWzgON0pF0U='
  'sha256-eIXWvAmxkr251LJZkjniEK5LcPF3NkapbJepohwYRIc='
  'sha256-ywDn4AkgLzJyrJIM2y/daMBkO4v1+WOHLIVFHbnbfH0=';
# (mesmos 3 hashes que o Chromium reportou como bloqueados acima)

$ node probe.mjs   # mesmo probe, mesma pagina, apos o fix
status 200
FOUND: CNJ inválido text appeared
```

Suite completa apos o fix:

```
$ npx vitest run
Test Files  80 passed (80)
     Tests  595 passed (595)

$ npx eslint . / npx astro check
0 errors em ambos
```
