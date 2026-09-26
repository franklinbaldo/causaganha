---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-akb9oz-evidence-ci-timeout-hardening-capture-invalid-process"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
kind: "runtime"
reference: ".github/workflows/cobogo-core-adoption-capture.yml; PR #1631, check run compare-product-surfaces (job 108027562847, run 36121420460)"
summary: "Apos o push do fix de onMount (fbf3f33), compare-product-surfaces continuou cancelled no mesmo ponto (~24min, mesmo timeout de job de 20min). Download de log do job cancelado retornou 404 (mesmo problema das 2 falhas anteriores -- logs de jobs cancelled por timeout nao ficam disponiveis via API de forma confiavel neste repositorio). Reproducao local mais rigorosa desta vez: nao so o caso isolado (probe.mjs), mas a sequencia COMPLETA e realista que o workflow executa contra o build 'after' (18 paginas em ordem, 2 viewports, incluindo processo.html?cnj=123 com --wait-for-selector) via Playwright real contra o build fixado (fbf3f33/4ece2ab) -- 100% das capturas completam rapido (a de CNJ invalido em 190ms), sem nenhum erro de console CSP. Isso nao prova que a CI vai passar (a rede/CPU real do runner do GitHub difere do sandbox, que intercepta HTTPS de terceiros com erro de certificado -- possivelmente mascarando um cenario onde DuckDB-WASM completa um fetch+compile real e pesado, e uma compilacao WASM sincrona longa poderia bloquear a re-renderizacao do Svelte mesmo com o estado ja atualizado), mas elimina com alta confianca qualquer bug de logica ainda presente no proprio fix. Constatado, via `npx playwright screenshot --help`, que --wait-for-selector nao tem timeout algum por padrao ('no timeout by default') -- ao contrario de capture() (limitado implicitamente pelo timeout de navegacao do proprio Playwright), capture_invalid_process() podia travar indefinidamente, exatamente o sintoma observado 3 vezes nesta rodada. Corrigido adicionando --timeout 30000 a capture_invalid_process() no workflow: nao resolve a causa raiz (seja ela qual for), mas garante que qualquer regressao futura neste ponto vira um TimeoutError rapido e legivel em vez de um hang silencioso de 20 minutos -- dado o custo de diagnostico real desta rodada (3 rodadas de push-espera-investiga, cada uma consumindo ate 25min de CI), esse bound sozinho ja e uma melhoria de robustez que vale a pena independente da causa exata."
---

# Evidencia: timeout adicionado a capture_invalid_process(), causa raiz do hang de CI permanece incerta

```
$ npx --yes playwright@1.55.0 screenshot --help
  --timeout <timeout>  timeout for Playwright actions in milliseconds, no timeout by default
```

Reproducao local da sequencia completa e realista (18 paginas x 2 viewports
+ 2 capturas de CNJ invalido, na ordem exata do workflow, contra o build
'after' fixado):

```
$ node probe_full.mjs
OK  index.html 1280,900 (86ms) navigated
...
OK  processo.html?cnj=123 1280,900 (190ms) selector found
OK  processo.html?cnj=123 390,844 (190ms) selector found
OK  publicacoes.html 1280,900 (88ms) navigated
...
DONE
```

Diff aplicado (`.github/workflows/cobogo-core-adoption-capture.yml`):

```diff
  capture_invalid_process() {
    ...
    npx --yes playwright@1.55.0 screenshot --browser chromium --viewport-size="$viewport" --full-page \
+     --timeout 30000 \
      --wait-for-selector='text=CNJ inválido' \
      ...
  }
```

Limitacao reconhecida: o log do job cancelado (108027562847) nao ficou
disponivel via API (404) apos varias tentativas ao longo de ~5 minutos,
entao nao foi possivel confirmar ao vivo qual capitura especifica travou
desta vez, nem se e a mesma de antes. A reproducao local (sequencia
completa, Playwright real, build identico) passou 100% limpa e rapida, o
que reduz a probabilidade de um bug de logica remanescente no fix, mas nao
descarta uma diferenca de ambiente (rede/CPU real do runner) que o sandbox
nao consegue replicar -- documentado honestamente, nao escondido, em
`next_move`.
