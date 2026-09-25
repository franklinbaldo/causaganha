---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-akb9oz-evidence-fix-processo-onmount-blocks-on-duckdb-init"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
kind: "test_green"
reference: "PR #1628, check run compare-product-surfaces (job 108014808147, run 36117464798); web/src/components/ProcessoLookup.svelte; web/src/components/ProcessoLookup.test.ts"
summary: "compare-product-surfaces (job 108014808147, apos o fix de hash allowlisting) ainda cancelou por timeout de 20min. Log completo do job (obtido via get_job_logs apos o job terminar, desta vez disponivel) mostra: a captura invalida de processo.html?cnj=123 no build 'before' (main, sem CSP) encontra 'CNJ inválido' as 09:17:32.58, ~1.4s apos 'Waiting for selector...' as 09:17:31.24. A captura identica no build 'after' (desta PR) nunca encontra o seletor -- 'Waiting for selector text=CNJ inválido...' as 09:17:51.18, seguido de nada ate 'The runner has received a shutdown signal' as 09:41:01.92 (23+ minutos depois, quando o job inteiro e morto pelo timeout). Como web/src/lib/duckdbSingleton.ts nao foi tocado por esta PR e e identico entre before/after, a diferenca teve que estar em outro lugar do diff. Reproduzido deterministicamente e rapido (nao 23 minutos) num teste unitario novo: mockar getDuckDB() para retornar uma Promise que nunca resolve, montar ProcessoLookup com window.location em '/causaganha/processo?cnj=123', RED confirmado -- o componente fica preso em 'Inicializando DuckDB-WASM…' e 'CNJ inválido' nunca aparece (waitFor expira). Causa raiz: onMount fazia 'await init()' incondicionalmente ANTES de ler o parametro ?cnj= da URL e chamar search() -- um bug de ordenacao pre-existente no componente, nunca antes exercitado por este job porque a CSP quebrava a hidratacao inteira do componente antes desta rodada corrigir isso (a falha anterior mascarava esta). GREEN apos mover 'init()' para disparo em segundo-plano (sem await) antes de processar o parametro da URL -- search() ja tinha o proprio guard (classifyCnjInput -> early return em 'invalid' antes de qualquer referencia a init()/DB) que so aguarda a conexao quando o formato e valido. Suite completa apos o fix: 80 arquivos, 601 testes, 100% verde (nenhuma regressao nos outros 9 testes de ProcessoLookup.test.ts nem nos demais arquivos ProcessoLookup.*.test.ts); eslint/astro check 0 erros."
---

# Evidencia: onMount bloqueava validacao de CNJ na inicializacao do DuckDB-WASM

```
$ mcp__github__get_job_logs(job_id=108014808147, run_id=36117464798)
...
2026-09-25T09:17:31.1776469Z Navigating to http://127.0.0.1:4173/causaganha/processo.html?cnj=123   # BEFORE (main)
2026-09-25T09:17:31.2419035Z Waiting for selector text=CNJ inválido...
2026-09-25T09:17:32.5804285Z Capturing screenshot into captures/processo-invalid-desktop-before.png   # ~1.4s, OK
...
2026-09-25T09:17:51.1268854Z Navigating to http://127.0.0.1:4174/causaganha/processo.html?cnj=123   # AFTER (esta PR)
2026-09-25T09:17:51.1828796Z Waiting for selector text=CNJ inválido...
2026-09-25T09:41:01.9170445Z ##[error]The runner has received a shutdown signal. ...   # 23+ min depois, job morto
```

Reproducao local, rapida e deterministica (`ProcessoLookup.test.ts`):

```
$ npx vitest run src/components/ProcessoLookup.test.ts -t "never resolves"
 ❯ shows "CNJ inválido" immediately from a ?cnj= URL param, even while getDuckDB() never resolves
  <p aria-busy="true">Inicializando DuckDB-WASM…</p>   # preso aqui, "CNJ inválido" nunca aparece
 Tests  1 failed | 9 skipped (10)
```

```diff
  onMount(() => {
-   (async () => {
-     await init();
-     if (cancelled) return;
-     const fromUrl = ...;
-     if (fromUrl) { input = fromUrl; await search(fromUrl, { updateUrl: false }); }
-   })();
+   void init();
+   (async () => {
+     const fromUrl = ...;
+     if (fromUrl) { input = fromUrl; await search(fromUrl, { updateUrl: false }); }
+   })();
```

```
$ npx vitest run src/components/ProcessoLookup.test.ts
 Test Files  1 passed (1)
      Tests  10 passed (10)

$ npx vitest run   # suite web completa
 Test Files  80 passed (80)
      Tests  601 passed (601)

$ npx eslint . / npx astro check
0 errors em ambos
```
