---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-r2xele-evidence-green-manifest-url-validation-ts"
run_id: "2026-09-25-exciting-mccarthy-r2xele"
kind: "test_green"
reference: "web/src/lib/processoCnj.ts (ArtifactUrlError, validateArtifactUrl, fonteUrls com avisos) + web/src/lib/processoCnj.test.ts"
summary: "Apos implementar ArtifactUrlError/validateArtifactUrl (mesma politica de causaganha.processos.service._validate_artifact_url: https-only, host archive.org, path /download/*.parquet, sem query/fragment, sem aspas simples, path local sem scheme passa) e adicionar o parametro avisos a fonteUrls() (descarta URL invalida com aviso em vez de propaga-la), os 5 testes RED passam a verde e os 113 pre-existentes continuam verdes -- 118/118. Os 4 pontos de chamada de fonteUrls() dentro de buscarProcesso() foram atualizados para passar avisos. 13 fixtures pre-existentes do arquivo de teste que usavam um host fake (https://ia/...) foram atualizadas para o formato https://archive.org/download/... exigido pela nova politica (find-and-replace mecanico, mesmas chaves de rota no fakeConn). Suite Vitest completa do repositorio (75 arquivos, 560 testes) tambem verde -- nenhuma regressao em nenhum outro modulo. eslint e astro check (typecheck) limpos (0 erros) sobre os arquivos tocados e o repositorio inteiro."
---

# Evidencia: GREEN apos implementar validateArtifactUrl (#1610, metade TypeScript)

```
$ npx vitest run src/lib/processoCnj.test.ts
 Test Files  1 passed (1)
      Tests  118 passed (118)

$ npx vitest run
 Test Files  75 passed (75)
      Tests  560 passed (560)

$ npx eslint src/lib/processoCnj.ts src/lib/processoCnj.test.ts
(sem output -- limpo)

$ npm run typecheck
Result (152 files):
- 0 errors
- 0 warnings
- 5 hints (pre-existentes, nao relacionados a esta mudanca)
```
