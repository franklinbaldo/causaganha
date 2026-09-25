---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-r2xele-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-r2xele"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Leitura integral no inicio da rodada. Fronteira CSS/Panda: novas paginas usam css()/recipes do preset cobogo; ProcessoLookup.svelte/PublicationSearch.svelte/SavedConsultations.svelte continuam com --papel-*/--s-* e scoped <style> -- nao relevante ao trabalho desta rodada (nenhuma mudanca visual). Contrato de query .qmd/contracts.ts nao se aplica (nao e um novo dataset para o frontend). Regras de manifesto djen_raw/sync-manifest.parquet sao do backend djen-backup, nao do arquivo alvo (web/src/lib/processoCnj.ts, que le indice_processual.parquet, um artefato diferente produzido por scripts/reconcile_processos.py). O trabalho selecionado (mirror TypeScript da validacao de URL de manifesto ja aplicada no lado Python por causaganha.processos.service._validate_artifact_url, issue #1610) e TDD puro em TypeScript (Vitest) sob web/src/lib/ -- nenhuma regra de ruff/TRY300 se aplica, mas o principio geral (nao adicionar tratamento de erro para cenarios que nao podem acontecer, TDD como fluxo padrao) foi seguido: RED com testes novos contra a API alvo (validateArtifactUrl, ArtifactUrlError) antes de qualquer mudanca de producao."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no inicio da rodada, conforme exigido
pelo contrato `AgentRun`. O trabalho desta rodada fica inteiramente em
`web/src/lib/processoCnj.ts` (TypeScript/Vitest), fora do escopo direto das
regras de estilo Python (ruff/TRY300) e da fronteira Panda/CSS -- nenhuma
regra do arquivo bloqueia ou reorienta o trabalho escolhido.
