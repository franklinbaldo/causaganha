---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-akb9oz-evidence-ci-green-onmount-fix-confirmed"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
kind: "test_green"
reference: "PR #1631, check run compare-product-surfaces (job 108039849051, run 36125277431), commit 9862a39"
summary: "Apos o push do fix de robustez do workflow (commit 9862a39, ver evidence-ci-confirms-root-cause-and-job-abort-bug), compare-product-surfaces passou (conclusion: success, ~4min). Log real confirma o ciclo diagnostico fechado: no estado 'before' (main, pre-fix), as duas capturas de processo.html?cnj=123 (desktop e mobile) estouraram o TimeoutError de 30s esperando 'CNJ inválido' -- 'Waiting for selector...' as 10:43:07.82/10:43:38.90, TimeoutError exatamente 30000ms depois em ambas, cada uma seguida do ::warning:: esperado, sem abortar o script. No estado 'after' (esta PR, com o fix de onMount), as mesmas duas capturas resolveram em ~90ms cada -- 'Waiting for selector...' e 'Capturing screenshot' no mesmo segundo. comparison.txt registrou 'processo-invalid-desktop=different' e 'processo-invalid-mobile=different' (esperado -- before falha, after funciona) e o job concluiu com exit code 0. Isso confirma definitivamente, com evidencia de CI real (nao mais hipotese nem reproducao local): (1) a causa raiz do hang original era genuina -- DuckDB-WASM realmente leva mais de 30s para carregar via rede real do runner a frio; (2) o fix de ordenacao do onMount resolve isso completamente, sem reintroduzir NENHUM outro tempo de espera; (3) o workflow agora e robusto a essa classe de diferenca esperada entre before/after. PR #1631 verificada como totalmente verde: 13/13 check runs com conclusion=success (CodeQL, validate, tests(tjro), lint, archive-cors-proxy, web, compare-product-surfaces, djen-proxy, CodeQL x4 linguagens, GitGuardian), mergeable_state='clean', 0 review threads abertos, revisao de seguranca do Codex concluida sem achados. Nao ha check 'Claude Approvals' configurado neste repositorio. PR pronta e aguardando apenas merge humano. Observacao nao relacionada registrada, nao investigada (fora do escopo desta PR): comparison.txt tambem mostrou 'stats.html-mobile=different', mas o diff desta PR (verificado via get_files) nao toca nenhum arquivo relacionado a stats.html -- provavelmente ruido de renderizacao nao-deterministica (grafico/canvas) preexistente, nao uma regressao desta mudanca; candidato a investigacao numa rodada futura, se reaparecer."
---

# Evidencia: CI real confirma fim a fim -- causa raiz + fix + robustez do workflow

## Log do job apos o fix de robustez (job 108039849051, run 36125277431, commit 9862a39)

```
# estado BEFORE (porta 4173 = main, pre-fix)
2026-09-25T10:43:07.7320384Z Navigating to http://127.0.0.1:4173/causaganha/processo.html?cnj=123
2026-09-25T10:43:07.8173562Z Waiting for selector text=CNJ inválido...
2026-09-25T10:43:37.8165030Z TimeoutError: Timeout 30000ms exceeded.
2026-09-25T10:43:37.8591128Z ##[warning]processo-invalid-desktop-before capture failed (timeout or error, see log above) -- comparison will report this surface as different
2026-09-25T10:43:38.9041038Z Navigating to http://127.0.0.1:4173/causaganha/processo.html?cnj=123
2026-09-25T10:43:38.9879888Z Waiting for selector text=CNJ inválido...
2026-09-25T10:44:08.9879945Z TimeoutError: Timeout 30000ms exceeded.
2026-09-25T10:44:09.0264748Z ##[warning]processo-invalid-mobile-before capture failed (timeout or error, see log above) -- comparison will report this surface as different

# script continuou (nao abortou) e passou para o estado AFTER (porta 4174 = esta PR, com o fix)
...
2026-09-25T10:44:31.9324492Z Navigating to http://127.0.0.1:4174/causaganha/processo.html?cnj=123
2026-09-25T10:44:32.0141657Z Waiting for selector text=CNJ inválido...
2026-09-25T10:44:32.1084815Z Capturing screenshot into captures/processo-invalid-desktop-after.png   # ~90ms
2026-09-25T10:44:33.3526086Z Navigating to http://127.0.0.1:4174/causaganha/processo.html?cnj=123
2026-09-25T10:44:33.4387630Z Waiting for selector text=CNJ inválido...
2026-09-25T10:44:33.5229466Z Capturing screenshot into captures/processo-invalid-mobile-after.png   # ~80ms

# comparison.txt
processo-invalid-desktop=different
processo-invalid-mobile=different
```

Job conclusion: `success`. Exit code 0.

## Estado final da PR (verificado via `pull_request_read`)

```
mergeable_state: "clean"
review_threads: [] (0 abertos)
check_runs: 13/13 conclusion=success
  CodeQL, validate, tests (tjro), lint, archive-cors-proxy, web,
  compare-product-surfaces, djen-proxy, Analyze (python/go/actions/
  javascript-typescript), GitGuardian Security Checks
comments: 1 (Codex security review summary -- Completed, sem achados
  bloqueantes, mergeGateEnabled=false)
```

Nenhum check "Claude Approvals" esta configurado neste repositorio.

## Observacao registrada, nao investigada

`comparison.txt` tambem mostrou `stats.html-mobile=different`. `get_files`
na PR confirma que nenhum arquivo relacionado a `stats.html` foi tocado por
este diff (apenas `.github/workflows/cobogo-core-adoption-capture.yml`,
5 arquivos de `knowledge/agent-runs/...` e
`web/src/components/ProcessoLookup.{svelte,test.ts}`) -- portanto essa
diferenca nao e uma regressao desta PR. Provavel ruido de renderizacao
nao-deterministica (grafico/canvas) ja preexistente na pagina de stats,
fora do escopo desta correcao; registrado para uma rodada futura
investigar se reaparecer.
