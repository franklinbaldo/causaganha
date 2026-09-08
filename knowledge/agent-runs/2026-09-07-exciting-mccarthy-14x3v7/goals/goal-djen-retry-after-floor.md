---
type: AgentGoal
id: "2026-09-07-exciting-mccarthy-14x3v7-goal-djen-retry-after-floor"
run_id: "2026-09-07-exciting-mccarthy-14x3v7"
goal: "Honor DJEN's real Retry-After instead of flooring it to 60s"
rationale: "web/src/lib/djenClient.ts's unwrap() correctly parses the DJEN proxy's Retry-After header on HTTP 429, then discards any value under 60 via Math.max(60, retryAfterSec) before throwing DjenRateLimitError. PublicationSearch.svelte consumes err.retryAfterSec directly to drive the on-screen cooldown countdown shown to the user. So a server-reported Retry-After of 5s (a light, short-lived throttle) is silently inflated into a fabricated 60s wait — a 12x-longer cooldown than the server actually asked for, with no documented policy anywhere in the repo (no comment, no doc, openapi/djen.yml is silent on a minimum) justifying the floor. The two existing 429 tests both used retry-after values >= 60 (60 and 90), so this code path had zero test coverage for the case where the floor actually changes behavior."
success_signal: "A new vitest case in web/src/components/__steps__/djen-search.steps.ts asserting retryAfterSec: 5 for a mocked 429 response with header retry-after: 5 fails RED against the unmodified code (observed retryAfterSec: 60), then passes GREEN once Math.max(60, retryAfterSec) is replaced by retryAfterSec alone. The full web suite (npx vitest run, 65 files) stays green, eslint reports 0 errors, and astro check reports 0 errors. A PR is opened and driven to a green, mergeable state."
status: "achieved"
---

# Goal: honrar o Retry-After real do DJEN

Encontrado por um agente Explore despachado nesta rodada para ampliar a busca além de `djen_backup/` (issues e PRs esgotadas; `circuit_breaker.py`/`credentials.py`/`djen.py` revisados sem novo defeito). `unwrap()` em `djenClient.ts` já faz o parsing correto do header `Retry-After`, mas descarta qualquer valor abaixo de 60s com `Math.max(60, retryAfterSec)` antes de lançar `DjenRateLimitError` — que `PublicationSearch.svelte` consome diretamente para o cronômetro de espera exibido ao usuário. Um `Retry-After: 5` do servidor vira uma espera fabricada de 60s, sem qualquer política documentada no repositório que justifique esse piso. Os dois testes existentes de 429 usam apenas valores ≥ 60, então esse caminho nunca foi coberto.
