---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-r2xele-evidence-red-manifest-url-validation-ts"
run_id: "2026-09-25-exciting-mccarthy-r2xele"
kind: "test_red"
reference: "web/src/lib/processoCnj.test.ts (novos describe('validateArtifactUrl', ...) e 2 testes novos em describe('fonteUrls', ...) e describe('buscarProcesso', ...))"
summary: "Os testes foram escritos primeiro contra a API alvo (validateArtifactUrl, ArtifactUrlError, fonteUrls(rows, fonte, avisos) com 3o parametro) que ainda nao existia em web/src/lib/processoCnj.ts. npx vitest run src/lib/processoCnj.test.ts antes de qualquer mudanca de producao falhou com 5 testes vermelhos: 2x TypeError: validateArtifactUrl is not a function (import inexistente), 1x fonteUrls descartando URL invalida (a antiga fonteUrls(rows, fonte) de 2 argumentos nao filtrava nada -- retornava as duas URLs em vez de descartar a maliciosa), e 1x o teste de integracao em buscarProcesso() mostrando que uma URL de arquivo_ia_url envenenada (host fora do allowlist) chegava intacta ao resultado em vez de degradar a fonte para ausente + aviso. Os 113 testes restantes do arquivo (comportamento pre-existente, nao tocado) continuaram verdes -- RED isolado exatamente ao comportamento novo pedido pela issue #1610."
---

# Evidencia: RED antes de implementar validateArtifactUrl (#1610, metade TypeScript)

```
$ npx vitest run src/lib/processoCnj.test.ts
 ❯ src/lib/processoCnj.test.ts (118 tests | 5 failed) 57ms
     × accepts a valid archive.org parquet URL: ... 6ms
     × accepts a valid archive.org parquet URL: ... 1ms
     × accepts a bare local path without a scheme (used by test fixtures) 0ms
     × drops an invalid URL and records an aviso instead of returning it — issue #1610 5ms
     × degrades a source to absent + aviso instead of crashing when the index has a poisoned arquivo_ia_url — issue #1610 2ms

TypeError: validateArtifactUrl is not a function
 ❯ src/lib/processoCnj.test.ts:678:12

AssertionError: expected [ …(2) ] to deeply equal [ Array(1) ]
- Expected
+ Received
  [
    "https://archive.org/download/djen-2024/a.parquet",
+   "https://evil.example/download/x/x.parquet",
  ]

AssertionError: expected false to be true // (djen.present should have been false)

 Test Files  1 failed (1)
      Tests  5 failed | 113 passed (118)
```

Confirma que a politica de validacao de URL de artefato de manifesto (host
allowlist, https-only, sem query/fragment, sem aspas simples embutidas,
path `/download/*.parquet`) nao existia em nenhuma forma no lado
TypeScript antes desta mudanca -- exatamente o gap que o corpo de `#1622`
ja apontava como follow-up.
