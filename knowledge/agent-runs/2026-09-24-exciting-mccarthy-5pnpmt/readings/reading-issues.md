---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-5pnpmt-reading-issues"
run_id: "2026-09-24-exciting-mccarthy-5pnpmt"
subject: "open_issues"
reference: "franklinbaldo/causaganha issues (issue_read #1609); docs/SECURITY_THREAT_MODEL.md Sec5"
finding: "#1609 ('security(relay): alinhar relays e DJEN proxy a politica minima de egress', TM-02, severidade Alta) e o proximo item explicito na ordem de execucao da Sec5 do threat model apos #1608/TM-01 (fechado pela rodada 1c8jcc) e #1615/TM-07 (fechado pela rodada 1c8jcc via #1619). Sem PR associada (closed_by_pull_requests.total_count=0). O corpo da issue descreve tres superficies concretas com gaps reais confirmados por leitura direta do codigo nesta rodada: (1) deployment/relay/function/main.py (Cloud Run/Python) aceita esquema http:// alem de https:// (so rejeita esquemas fora de {http,https}), aceita qualquer metodo HTTP sem allowlist, nao limita tamanho de corpo/resposta, e nao remove explicitamente Authorization/Cookie do encaminhamento (so remove headers hop-by-hop, Host e Content-Length); (2) deployment/relay-cf/src/index.js (Cloudflare Worker/JS) ja e HTTPS-only e GET/HEAD/POST-only com stripping mais forte (remove x-forwarded-*, cf-*, true-client-ip), mas tambem nao limita tamanho de corpo/resposta nem remove Authorization/Cookie explicitamente; (3) deployment/djen_proxy.go (proxy Go fixed-host para comunicaapi.pje.jus.br) nao tem nenhuma autenticacao, aceita qualquer metodo HTTP nos paths permitidos, e a whitelist de paths (/api/, /swagger/, /comunicacao, /login) e mais ampla que o unico uso real confirmado no codigo (GET .../api/v1/caderno/{tribunal}/{data}/D via src/djen_backup/djen.py e GET .../api/v1/comunicacao/tribunal via src/djen_backup/tribunais.py) -- /swagger/ e buscado direto do host oficial por scripts/vendor_pje_swagger.py, nao via proxy, e nenhum caller do repo usa /login. Ja existe tests/deployment/relay/test_main.py cobrindo host allowlist, token e header stripping do relay Python, mas sem casos para http:// permitido, metodo livre ou ausencia de limite de tamanho -- os gaps que esta rodada fecha."
---

# Leitura: issue selecionada (#1609/TM-02)

Leitura integral de `#1609` via `issue_read`. E o proximo item nao
reivindicado da ordem de execucao explicita da Sec5 do threat model
(`docs/SECURITY_THREAT_MODEL.md`), confirmado pela leitura de PRs
abertas (nenhuma toca os relays ou o DJEN proxy) e pelo `next_move`
da rodada anterior (`1c8jcc`). Leitura direta dos tres arquivos-alvo
confirma cada gap que o corpo da issue lista como esperado (HTTPS-only,
metodos fechados, headers sensiveis removidos, limites de tamanho) e
localiza, para o DJEN proxy, que o whitelist de rotas atual e mais
amplo que qualquer uso real do proxy no codigo do repositorio.
