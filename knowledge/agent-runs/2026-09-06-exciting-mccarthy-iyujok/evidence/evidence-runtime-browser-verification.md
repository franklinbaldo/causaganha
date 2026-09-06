---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-iyujok-evidence-runtime-browser-verification"
run_id: "2026-09-06-exciting-mccarthy-iyujok"
goal_id: "2026-09-06-exciting-mccarthy-iyujok-goal-mcpconfigcard-a11y"
kind: "runtime"
reference: "npm run build (web/dist), served locally on 127.0.0.1:4501/causaganha/, driven with Playwright (chromium at /opt/pw-browsers/chromium-1194) against the built agentes.html"
summary: "Real Chromium check against the built /agentes page confirmed: the <pre> element carries tabindex=\"0\", role=\"region\", and aria-label=\"Configuração MCP (stdio), rolável horizontalmente\" as rendered HTML (not just source); calling .focus() on it moves document.activeElement to the PRE element itself (keyboard focus genuinely lands on the scroll region, not lost to <body>); and with clipboard permissions granted via context.grantPermissions, clicking 'Copiar configuração' inside the #conectar section still produces the exact expected status text 'Configuração copiada.', proving the copy-to-clipboard behavior is unaffected by the accessibility fix. A temporary local playwright@1.55.0 install (matching the CI workflow's pinned version) was used for this check via `npm install --no-save`, with PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 already set in the environment so no new browser binary was fetched; node_modules/playwright and package-lock.json/package.json drift from this temporary install were left untouched by git (only web/src/components/McpConfigCard.svelte and the new test file were committed) since `npm install --no-save` does not modify package.json/package-lock.json."
---

# Evidência runtime: verificação em navegador real

Build real do site, servido localmente e inspecionado com Chromium via Playwright: o `<pre>` tem `tabindex`/`role`/`aria-label` corretos no HTML renderizado, recebe foco de teclado de fato, e o botão de copiar continua funcionando (`"Configuração copiada."` após clique com permissão de clipboard concedida). Nenhuma regressão comportamental.
