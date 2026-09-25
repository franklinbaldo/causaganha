---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-akb9oz-evidence-ci-fix-a11y-audit-csp-inline-script"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
kind: "ci"
reference: "PR #1628, check run compare-product-surfaces (job 107991168401, run 36110033578), scripts/check_surface_accessibility.mjs"
summary: "CI de PR #1628 (commit 2cd441f, apos o fix do rename _redirectStubs) marcou compare-product-surfaces como cancelled: o passo 'Install and build both states' passou (confirma que a CSP nao quebra o build em si), mas o passo seguinte 'Audit semantic accessibility on desktop and mobile' falhou (conclusion: failure) e o job travou no passo seguinte ate estourar o timeout de 20min e ser cancelado -- download de log do job cancelado retornou 404/zip vazio (log ainda nao arquivado pelo GitHub), entao a causa raiz foi diagnosticada estruturalmente e confirmada por reproducao local, nao por leitura direta do log de CI. scripts/check_surface_accessibility.mjs injeta axe-core via page.addScriptTag({content: axe.source}) DEPOIS de page.goto() -- isso cria uma <script> tag inline real no DOM, sujeita a CSP da pagina. A CSP desta PR (script-src 'self', sem unsafe-inline) bloqueia exatamente esse tipo de injecao. Reproduzido localmente (Playwright 1.55.0 + Chromium pre-instalado em /opt/pw-browsers, fora do repositorio, em scratchpad): pagina servida com a CSP exata desta PR, page.addScriptTag({content}) falha com 'Refused to execute inline script because it violates ... script-src 'self'' (mensagem de console CSP capturada verbatim); page.addInitScript({content}), que roda via CDP Page.addScriptToEvaluateOnNewDocument e por isso nao e sujeito a CSP de pagina, funciona (axe fica disponivel como window.axe). Corrigido movendo a injecao para context.addInitScript({content: axe.source}) uma vez por contexto (viewport), antes de qualquer navegacao, e removendo o addScriptTag pos-navegacao. Validado end-to-end: build real do site com a CSP desta PR, servido localmente, script corrigido (copia com apenas o override de executablePath para contornar um mismatch de versao de binario Playwright do sandbox local, nao presente no CI) rodado contra as 7 rotas x 2 viewports -- 0 violacoes axe serias/criticas, 0 controles ausentes, 0 falhas de foco, exit code 0 (equivalente ao criterio de sucesso do job real)."
---

# Evidencia: CI cancelado por audit de acessibilidade quebrado pela CSP, corrigido

```
$ mcp__github__actions_get(method=get_workflow_job, resource_id=107991168401)
{"conclusion":"cancelled", "steps":[
  ...,
  {"name":"Install and build both states","conclusion":"success",...},
  {"name":"Install Chromium","conclusion":"success",...},
  {"name":"Serve both builds","conclusion":"success",...},
  {"name":"Audit semantic accessibility on desktop and mobile","conclusion":"failure",...},
  {"name":"Capture desktop and mobile product surfaces","status":"in_progress",...}  # travou ate timeout
]}
```

Reproducao local (scratchpad, fora do repositorio, playwright@1.55.0 + axe-core@4.10.3):

```
--- attempt 1: page.addScriptTag({content}) AFTER navigation (abordagem original) ---
[console] error Refused to execute inline script because it violates the following
Content Security Policy directive: "script-src 'self'". Either the 'unsafe-inline'
keyword, a hash (...), or a nonce (...) is required to enable inline execution.
addScriptTag threw: page.addScriptTag: Refused to execute inline script ...

--- attempt 2: page.addInitScript({content}) BEFORE navigation (fix proposto) ---
addInitScript result: hasAxe = true
```

Validacao end-to-end contra o build real desta PR (site-status.json etc.
sinteticos, mesmas fixtures do workflow `cobogo-core-adoption-capture.yml`):

```
$ node check.mjs   # copia do scripts/check_surface_accessibility.mjs corrigido
...
"serious_or_critical_axe_violations": []   # em todas as 7 rotas x 2 viewports
$ echo $?
0
```

Diff aplicado (`scripts/check_surface_accessibility.mjs`):

```diff
 for (const viewport of viewports) {
   const context = await browser.newContext({ viewport });
+  await context.addInitScript({ content: axe.source });
   for (const route of routes) {
     ...
-    await page.addScriptTag({ content: axe.source });
     const violations = await page.evaluate(async () => {
```
