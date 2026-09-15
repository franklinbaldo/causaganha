---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-q4zn8q-check-wrangler-dry-run"
run_id: "2026-09-15-exciting-mccarthy-q4zn8q"
goal_id: "2026-09-15-exciting-mccarthy-q4zn8q-goal-archive-cors-proxy"
command: "cd deployment/archive-cors-proxy && npx wrangler deploy --dry-run"
result: "passed"
summary: "Wrangler valida e empacota o Worker sem erro (Total Upload 3.32 KiB / gzip 1.33 KiB, No bindings found), sem precisar de credenciais Cloudflare reais -- confirma que o codigo esta pronto para deploy assim que IA_ACCESS_KEY-equivalente (credenciais Cloudflare) estiver disponivel; deploy real permanece bloqueado nesta sessao, mesma classe de bloqueio do cluster #1468-1472."
---

# Check: wrangler deploy --dry-run

`npx wrangler deploy --dry-run` roda sem autenticacao real (nao contata a
API da Cloudflare para um dry-run) e confirma que `wrangler.jsonc` +
`src/index.js` formam um Worker valido e publicavel. O deploy real
(`npm run deploy`) continua bloqueado nesta sessao por falta de
credenciais Cloudflare -- registrado como proximo passo explicito, nao
tentado.
