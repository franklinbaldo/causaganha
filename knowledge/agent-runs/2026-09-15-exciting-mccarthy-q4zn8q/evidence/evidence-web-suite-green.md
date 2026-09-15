---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-q4zn8q-evidence-web-suite-green"
run_id: "2026-09-15-exciting-mccarthy-q4zn8q"
goal_id: "2026-09-15-exciting-mccarthy-q4zn8q-goal-archive-cors-proxy"
kind: "test_green"
reference: "web/ (npx vitest run, npm run lint, npm run typecheck) apos web/src/lib/archiveProxyBase.ts + wiring em DuckDBExplorer.svelte e explorador.astro"
summary: "545/545 testes vitest passando em web/ (inclui os 3 novos testes de archiveProxyBase e os 19 testes existentes de DuckDBExplorer, incluindo cors-block-classification, sem regressao). npm run lint: 0 erros (so avisos preexistentes em styled-system/ gerado). npm run typecheck (astro check): 0 erros, 0 avisos novos."
---

# Evidencia: suite web verde apos o wiring do proxy

`web/src/lib/archiveProxyBase.ts` (funcao pura `resolveArchiveDownloadBase`)
foi escrita com `web/src/lib/archiveProxyBase.test.ts` cobrindo: sem proxy
configurado -> `https://archive.org/download` (comportamento identico ao
anterior); com proxy configurado -> `{proxy}/download`, com e sem barra
final.

`DuckDBExplorer.svelte` passou a derivar `IA_BASE` dessa funcao a partir de
uma nova prop `archiveProxyBase` (default `''`, preservando o
comportamento atual quando nao configurada). `explorador.astro` passa
`archiveProxyBase={import.meta.env.PUBLIC_ARCHIVE_PROXY_BASE ?? ''}` --
vazio ate o Worker ser publicado e a variavel de build configurada.

Resultados ao vivo nesta rodada:
- `npx vitest run` (raiz de `web/`): `Test Files 75 passed (75)` /
  `Tests 545 passed (545)`, incluindo os 3 novos testes de
  `archiveProxyBase` e os 19 testes existentes ligados a
  `DuckDBExplorer.svelte` (cors-block-classification,
  dataset-availability, query-error-classification) sem nenhuma
  regressao.
- `npm run lint`: 0 erros (43 avisos, todos preexistentes em
  `styled-system/*.d.ts` gerado, nao relacionados a esta mudanca).
- `npm run typecheck` (`astro check`): `0 errors, 0 warnings, 5 hints`
  (hints preexistentes, nao relacionados a esta mudanca).
