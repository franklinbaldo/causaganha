---
type: AgentGoal
id: "2026-09-15-exciting-mccarthy-q4zn8q-goal-archive-cors-proxy"
run_id: "2026-09-15-exciting-mccarthy-q4zn8q"
goal: "Implementar o workaround sugerido pela issue #1482: um Cloudflare Worker que faz proxy de archive.org/download/{item}/{file} adicionando Access-Control-Allow-Origin, e ligar DuckDBExplorer.svelte a ele de forma configuravel, com TDD real (RED antes, GREEN depois)."
rationale: "Issue #1482 diagnostica e confirma ao vivo (Chromium headless real, PR #1489/#1491) que archive.org/download/... nao envia Access-Control-Allow-Origin, bloqueando read_parquet() no navegador. O corpo da issue sugere explicitamente 'proxying through the dashboard's own origin' como correcao, mas nenhuma rodada ate agora implementou isso -- so a deteccao/classificacao (describeCorsBlockedDataset) existe em producao. Diferente do cluster #1468-1472, este trabalho nao depende de IA_ACCESS_KEY/IA_SECRET_KEY: o codigo do Worker e seus testes (Vitest, fetch mockado, mesmo padrao de deployment/relay-cf) podem ser escritos e verificados sem nenhuma credencial de deploy real, e o deploy real (wrangler) fica documentado como proximo passo explicitamente bloqueado por credenciais Cloudflare ausentes -- mesma classe de bloqueio ja registrada para o cluster IA, nao um novo tipo de blocker."
success_signal: "Novo diretorio deployment/archive-cors-proxy/ com um Worker (src/index.js) cujos testes (test/index.test.js, Vitest) comecam RED (escritos antes do Worker existir / contra um Worker vazio) e terminam GREEN depois da implementacao, cobrindo: GET/HEAD permitidos e streaming do corpo, POST/PUT rejeitados (405), caminho fora do allowlist (fora de /download/djen-*) rejeitado (403), Range/Accept-Ranges/Content-Range preservados no proxy (necessario para DuckDB-WASM), Access-Control-Allow-Origin adicionado na resposta, erro upstream vira 502. web/src/components/DuckDBExplorer.svelte ganha uma forma configuravel (prop ou funcao pura testavel) de apontar para o proxy em vez de archive.org direto, com teste unitario cobrindo a resolucao da URL base (com e sem proxy configurado), sem quebrar o comportamento padrao existente (sem proxy configurado = exatamente o comportamento atual, incluindo a deteccao de cors-blocked). npm test em deployment/archive-cors-proxy/ e em web/ ficam verdes; uv run pytest -q, ruff check e ruff format --check continuam verdes. PR aberta contra main."
status: "achieved"
---

# Goal: proxy CORS para archive.org (issue #1482)

Primeira tentativa real de implementar a correcao sugerida pela propria
issue #1482, apos varias rodadas terem confirmado o diagnostico e fechado
apenas a deteccao/classificacao e a regressao em CI. Segue o padrao ja
validado em `deployment/relay-cf/` (Worker minimalista, allowlist
explicita, testes Vitest com `fetch` mockado) em vez de inventar um novo
padrao de deploy.
