---
type: AgentGoal
id: "2026-09-24-exciting-mccarthy-5pnpmt-goal-relay-egress-policy"
run_id: "2026-09-24-exciting-mccarthy-5pnpmt"
goal: "Fechar #1609/TM-02: alinhar o relay Python (deployment/relay/function/main.py) e o relay Cloudflare (deployment/relay-cf/src/index.js) a uma politica minima de egress equivalente -- HTTPS-only, metodos fechados (GET/HEAD/POST), headers sensiveis (Authorization/Cookie/Set-Cookie) nunca encaminhados, e budgets explicitos de tamanho de corpo/resposta -- mantendo os casos validos atuais de STJ/TJRO/TSE."
rationale: "Leitura direta do codigo (reading-issues) confirmou os gaps que a issue #1609/TM-02 (severidade Alta no threat model) descreve: o relay Python aceita http:// alem de https://, nao restringe metodo, nao remove Authorization/Cookie do encaminhamento e nao limita tamanho de corpo/resposta -- um token roubado ou um chamador comprometido pode usar o relay como proxy HTTP generico contra qualquer host da allowlist, com qualquer metodo, encaminhando credenciais arbitrarias e sem teto de banda/memoria. O relay CF ja fecha metodo e esquema mas compartilha os dois ultimos gaps (headers sensiveis, budgets de tamanho). tests/deployment/relay/test_main.py ja cobre allowlist de host/token/stripping hop-by-hop, mas nao esses gaps -- material real para TDD."
success_signal: "tests/deployment/relay/test_main.py cresce com casos novos que provam, contra o main.py real: (1) http://<host-allowlistado> e rejeitado com 403 (hoje passa); (2) PUT/PATCH/DELETE/TRACE/CONNECT sao rejeitados com 405, GET/HEAD/POST continuam passando; (3) Authorization/Cookie enviados pelo chamador nunca aparecem nos headers encaminhados ao upstream; (4) um corpo de requisicao acima do teto configurado e rejeitado com 413 antes de qualquer chamada ao upstream; (5) uma resposta upstream acima do teto e truncada/rejeitada em vez de materializada inteira em memoria. deployment/relay-cf/test/index.test.js cresce com os casos equivalentes (3)-(4)-(5) via vitest. Cada caso falha (RED) contra o codigo atual antes da mudanca e passa (GREEN) depois. uv run ruff check/format --check e uv run pytest -q ficam verdes no lado Python; npm test fica verde no lado CF (quando o ambiente permitir instalar as dependencias do vitest)."
status: "achieved"
---

# Objetivo: politica minima de egress dos relays (#1609/TM-02)

Trabalho principal desta rodada, proximo item nao reivindicado da
ordem de execucao da Sec5 do threat model apos `#1608`/TM-01 e
`#1615`/TM-07 (ambos fechados pela rodada anterior, `1c8jcc`).
Escopo desta rodada cobre os dois relays HTTP (Python/Cloud Run e
JS/Cloudflare Worker); o DJEN proxy Go (`deployment/djen_proxy.go`)
fica registrado como gap remanescente em `next_move` (ver
`decision-scope-two-relays-not-go-proxy`).
