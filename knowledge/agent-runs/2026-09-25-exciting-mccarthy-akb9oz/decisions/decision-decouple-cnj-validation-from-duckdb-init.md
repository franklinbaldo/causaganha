---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-akb9oz-decision-decouple-cnj-validation-from-duckdb-init"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
question: "compare-product-surfaces kept hanging (20min timeout) on this PR's build even after the CSP-hydration fix: CI logs show the 'before' (main, no CSP) capture of processo.html?cnj=123 finds 'CNJ inválido' in ~1.4s, but the identical capture against 'after' (this PR's build) never finds it, hanging until the job is killed. Both builds run the same duckdbSingleton.ts, untouched by this PR -- so what's actually different, and whose bug is it to fix?"
choice: "Reproduced deterministically in a fast unit test (mock getDuckDB() to never resolve, mount with ?cnj=123 in the URL): ProcessoLookup.svelte's onMount awaited init() (the DuckDB-WASM connection) BEFORE reading the URL's cnj param and calling search() -- so a syntactically invalid CNJ, which needs zero database access to reject, could never render until DB init settled. Fixed onMount to fire init() in the background (not awaited) and process the URL param immediately; search() already awaits init() itself, but only for a syntactically valid CNJ that actually needs a query. Treated as this PR's bug to fix, not CI infrastructure to route around."
rationale: "This is a genuine, user-facing product bug, not a CI-only artifact: any real visitor to /processo?cnj=<invalid> whose browser/network makes DuckDB-WASM's real instantiate() call slow or stuck (plausible on this plain static site, which sets no COOP/COEP headers DuckDB-WASM's threaded/COI bundle variant benefits from) would see the app stuck on 'Inicializando DuckDB-WASM…' forever instead of the instant, DB-free format-validation message the UI is supposed to show. Before this PR's CSP fix, ProcessoLookup never hydrated at all under the new CSP (a different bug, already fixed), which is exactly why this ordering bug had never been exercised by compare-product-surfaces before -- the job's own CSP-caused failure was masking this one. Routing around it in the test workflow (e.g. giving capture_invalid_process's --wait-for-selector a timeout so CI merely tolerates the hang) would leave the real bug live in production and merely stop the job from usefully catching it. The fix is minimal and strictly a reordering: search()'s own invalid-format short-circuit (checked before touching the database at all) already existed and needed no change; only onMount's own unconditional pre-await of init() was wrong. Verified with a new regression test that reproduces the exact CI failure deterministically and fast (getDuckDB() mocked to a promise that never resolves, mount with ?cnj=123, assert 'CNJ inválido' still renders) -- this is a real, fast, always-on regression gate for a bug a 20-minute CI job would otherwise be the only thing catching."
---

# Decisao: desacoplar validacao de formato de CNJ da inicializacao do DuckDB-WASM

`compare-product-surfaces` continuou travando apos o fix de hidratacao via
CSP hash allowlisting -- os logs do job mostraram que o build `before`
(main, sem CSP) encontra 'CNJ inválido' em ~1.4s, mas o build `after`
(desta PR) nunca encontra, travando ate o timeout de 20min do job.
Reproduzido deterministicamente e rapido num teste unitario novo
(`ProcessoLookup.test.ts`): `onMount` esperava `init()` (conexao
DuckDB-WASM) terminar ANTES de ler o parametro `?cnj=` da URL e chamar
`search()` -- entao um CNJ sintaticamente invalido, que nao precisa de
banco de dados nenhum para ser rejeitado, nunca renderizava ate a conexao
assentar. Corrigido disparando `init()` em segundo plano (sem `await`) e
processando o parametro da URL imediatamente; `search()` ja tinha o
proprio guard que so toca o banco quando o formato e valido. Tratado como
bug real de produto desta PR, nao como infraestrutura de CI a contornar --
ver `evidence-fix-processo-onmount-blocks-on-duckdb-init`.
