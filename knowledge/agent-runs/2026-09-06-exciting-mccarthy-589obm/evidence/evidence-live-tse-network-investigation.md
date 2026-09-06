---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-589obm-evidence-live-tse-network-investigation"
run_id: "2026-09-06-exciting-mccarthy-589obm"
goal_id: "2026-09-06-exciting-mccarthy-589obm-goal-fix-backlog-985-category"
kind: "runtime"
reference: "curl -I against https://cdn.tse.jus.br/estatistica/sead/odsele/processual/{processo_eleitoral_2026,processos_eleitorais_assuntos_2026,processos_eleitorais_decisoes_2026}.zip and https://cdn.tse.jus.br/estatistica/sead/, curl against https://dadosabertos.tse.jus.br/api/3/action/package_show?id=processual-2026, and a Playwright (Chromium) page.goto against the first ZIP URL; getent hosts cdn.tse.jus.br"
summary: "getent hosts cdn.tse.jus.br resolves (2 Akamai edgesuite IPv6 addresses) and curl completes a TCP/TLS handshake ('HTTP/1.1 200 Connection Established' from the local proxy, then 'HTTP/2 403' from the origin) against every path tried, including a bare directory listing and the CKAN API on a different subdomain — ruling out both DNS failure (the story every prior round recorded) and a path-specific block. Reading the actual response body (not just the status line) shows an Akamai edgesuite.net 'Access Denied' HTML page with a unique reference/error ID each time, confirming the 403 originates from TSE's own WAF/CDN layer, not from this environment's outbound proxy (whose own /__agentproxy/status was also checked and shows no host-level denylist for tse.jus.br). Adding a full browser User-Agent, Accept-Language, and a Referer of https://www.tse.jus.br/ made no difference. A real headless-Chromium navigation (Playwright, /opt/pw-browsers/chromium) to the same ZIP URL failed with net::ERR_CONNECTION_RESET rather than rendering the 403 page, a stronger signal (TLS/connection-level rejection under a full browser stack) pointing at a network-origin block (e.g. geo-fencing to Brazil) rather than a header/user-agent-based bot filter that request-crafting could route around."
---

# Evidência de runtime: investigação de rede viva contra o TSE

`getent hosts cdn.tse.jus.br` resolve; `curl` completa o handshake TCP/TLS mas recebe 403 "Access Denied" da própria Akamai (corpo HTML confirmado, não só o código de status) em todo caminho testado, incluindo a API CKAN em outro subdomínio. Uma navegação real via Chromium headless falhou com `net::ERR_CONNECTION_RESET`. Conjunto de sinais consistente com bloqueio de rede/geográfico na origem, não com falta de cabeçalhos de navegador.
