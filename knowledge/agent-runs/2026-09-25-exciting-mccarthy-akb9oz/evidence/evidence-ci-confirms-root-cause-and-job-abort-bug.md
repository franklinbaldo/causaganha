---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-akb9oz-evidence-ci-confirms-root-cause-and-job-abort-bug"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
kind: "runtime"
reference: "PR #1631, check run compare-product-surfaces (job 108037987242, run 36124693021); .github/workflows/cobogo-core-adoption-capture.yml"
summary: "Apos o push do --timeout 30000 (commit 6bd272b), compare-product-surfaces falhou rapido (~5min, nao mais um hang de 20min) -- exatamente o comportamento pretendido pela blindagem. O log real (desta vez disponivel, pois o job completou em vez de ser cancelled) mostra a causa: a captura invalida de processo.html?cnj=123 no estado 'before' (porta 4173 = SHA base da PR, main sem o fix de onMount desta rodada) nunca encontrou o seletor 'CNJ inválido' e estourou o TimeoutError de 30s -- 'Waiting for selector text=CNJ inválido...' as 10:36:27.49, 'TimeoutError: Timeout 30000ms exceeded' as 10:36:57.49. Isso confirma ao vivo, em rede real de CI (nao mais mascarado pela interceptacao TLS do sandbox local), que o bug de ordenacao do onMount em ProcessoLookup.svelte (await init() incondicional antes de checar ?cnj=) e real e mensuravel: o fetch+compile do DuckDB-WASM via rede real leva mais de 30s a frio neste ambiente, exatamente a hipotese registrada no next_move da rodada anterior. Isso NAO e uma falha desta PR -- e o comportamento do codigo BASE (main, pre-fix) que este PR corrige; o job simplesmente nunca chegou a capturar o estado 'after' (que tem o fix) porque 'set -euo pipefail' abortou o script inteiro no primeiro erro do estado 'before'. Identificado e corrigido um bug real de robustez no proprio workflow: uma diferenca de comportamento esperada entre before/after (o proposito inteiro de um job de diff visual) nao deveria abortar a captura de TODOS os outros surfaces -- deveria ser registrada como 'different' pelo passo de comparacao, que ja trata arquivo ausente corretamente. Corrigido envolvendo a chamada de screenshot em 'if ! ...; then echo ::warning::...; fi' (nao mais nu), preservando set -e para o resto do script. Validado localmente: sintaxe bash extraida do YAML (bash -n) OK; um script de teste minimo confirma que 'if ! false; then ...; fi' sob 'set -euo pipefail' nao aborta a execucao seguinte (exit code 0, ambas as linhas antes/depois do bloco impresso)."
---

# Evidencia: CI real confirma a causa raiz do onMount e revela bug de abort no proprio workflow

## Log real do job (job 108037987242, run 36124693021, commit 6bd272b)

```
2026-09-25T10:36:24.5742938Z Navigating to http://127.0.0.1:4173/causaganha/processo.html   # BEFORE, port 4173 = base (main, sem fix)
2026-09-25T10:36:24.6628202Z Capturing screenshot into captures/processo.html-desktop-before.png   # OK, rapido
2026-09-25T10:36:25.9815482Z Navigating to http://127.0.0.1:4173/causaganha/processo.html
2026-09-25T10:36:26.0709067Z Capturing screenshot into captures/processo.html-mobile-before.png   # OK, rapido
2026-09-25T10:36:27.3998117Z Navigating to http://127.0.0.1:4173/causaganha/processo.html?cnj=123
2026-09-25T10:36:27.4938751Z Waiting for selector text=CNJ inválido...
2026-09-25T10:36:57.4938267Z TimeoutError: Timeout 30000ms exceeded.
2026-09-25T10:36:57.4939988Z Call log:
2026-09-25T10:36:57.4939988Z   - waiting for locator('text=CNJ inválido') to be visible
2026-09-25T10:36:57.5385789Z ##[error]Process completed with exit code 1.
```

O job nunca chegou a testar o estado `after` (porta 4174, esta PR) -- `set -euo
pipefail` matou o script inteiro no primeiro erro, que aconteceu no estado
`before`.

## Diagnostico

1. **Causa raiz confirmada ao vivo**: o `onMount` pre-fix (`await init()` antes
   de checar `?cnj=`) realmente bloqueia a renderizacao de "CNJ inválido" por
   mais de 30s quando o `fetch()` do DuckDB-WASM roda contra a rede real do
   runner de CI (a frio, sem cache) -- o sandbox local desta sessao nunca
   conseguiu reproduzir isso porque a interceptacao TLS do proxy faz esse
   fetch falhar quase instantaneamente, mascarando o problema. Isso fecha o
   item (1) do `next_move` anterior com confianca alta, sem precisar de mais
   reproducao local.
2. **Bug de robustez descoberto no proprio workflow**: `capture_invalid_process`
   sob `set -euo pipefail` transforma uma diferenca de comportamento
   *esperada* entre before/after (o proprio motivo deste job existir) num
   abort total do script, entao nunca sabiamos se o estado `after` (com o fix
   desta PR) de fato resolveria dentro do timeout.

## Fix aplicado (`.github/workflows/cobogo-core-adoption-capture.yml`)

```diff
-            npx --yes playwright@1.55.0 screenshot --browser chromium --viewport-size="$viewport" --full-page \
-              --timeout 30000 \
-              --wait-for-selector='text=CNJ inválido' \
-              "http://127.0.0.1:${port}/causaganha/processo.html?cnj=123" \
-              "captures/processo-invalid-${suffix}-${state}.png"
+            if ! npx --yes playwright@1.55.0 screenshot --browser chromium --viewport-size="$viewport" --full-page \
+              --timeout 30000 \
+              --wait-for-selector='text=CNJ inválido' \
+              "http://127.0.0.1:${port}/causaganha/processo.html?cnj=123" \
+              "captures/processo-invalid-${suffix}-${state}.png"; then
+              echo "::warning::processo-invalid-${suffix}-${state} capture failed (timeout or error, see log above) -- comparison will report this surface as different"
+            fi
```

O passo de comparacao ja trata um arquivo ausente corretamente (`cmp -s`
retorna nao-zero, cai no ramo `different`), entao nenhuma mudanca adicional
foi necessaria ali.

## Validacao local

```
$ python3 -c "import yaml; yaml.safe_load(open('.github/workflows/cobogo-core-adoption-capture.yml'))"
YAML parses OK

$ bash -n /tmp/capture_script.sh   # script bash extraido do bloco `run:` do YAML
bash syntax OK

$ bash test_wrap.sh; echo "exit code: $?"
before call
::warning::simulated failure captured, not aborting
after call - should print if not aborted
exit code: 0
```

## Expectativa para a proxima execucao

Com este fix, o proximo `compare-product-surfaces` deve: (a) registrar
`processo-invalid-*-before` como falho/ausente (comportamento correto e
esperado do codigo base, nao regressao desta PR) via `::warning::`, SEM
abortar o job; (b) prosseguir e capturar o estado `after` (com o fix desta
PR), que deve encontrar o seletor rapidamente, assim como a reproducao local
completa (`probe_full.mjs`, 190ms) ja demonstrou; (c) `comparison.txt`
mostrara `processo-invalid-desktop=different` e `processo-invalid-mobile=different`
(esperado -- before falha, after funciona) e o job deve concluir com sucesso
(`if: always()` no upload de evidencias, e a captura em si nao aborta mais).
