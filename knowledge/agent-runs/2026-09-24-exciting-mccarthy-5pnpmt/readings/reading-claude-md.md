---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-5pnpmt-reading-claude-md"
run_id: "2026-09-24-exciting-mccarthy-5pnpmt"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Leitura integral no inicio da rodada (conteudo entregue no proprio system prompt da sessao). Confirma o essencial ja estabelecido por 7+ rodadas anteriores da mesma janela de trabalho (2026-09-24/25): sync-manifest.parquet e a unica fonte da verdade do djen-backup, djen_raw e codigo de transporte HTTP (nunca veredito de disponibilidade -- 200-sem-URL e absent, 403 nunca e absent), a fronteira Panda/Svelte (tres ilhas legadas usam --papel-*/--s-*, paginas novas usam css()/recipes do preset cobogo), e as regras de estilo Python (ruff estrito, TRY300/TRY301/TRY401, sem except Exception generico fora do bulkhead da ADR 0011, from __future__ import annotations, uv run ruff check/format --check/pytest -q antes de commitar). O trabalho selecionado nesta rodada (issue #1609/TM-02 -- fechar a politica minima de egress dos relays HTTP e do DJEN proxy em deployment/relay/, deployment/relay-cf/ e deployment/djen_proxy.go) e infraestrutura de deploy fora das areas de dominio normadas por este arquivo (nao toca djen-backup nem os contratos de query .qmd nem a fronteira CSS), mas a secao 'Antes de committing' se aplica integralmente e foi seguida em cada superficie tocada (Python via ruff/pytest, JS via vitest, Go via 'go vet'/'go test')."
---

# Leitura: CLAUDE.md

Leitura integral do guia do projeto no inicio da rodada, conforme
exigido pelo contrato `AgentRun`. Nenhuma das areas de dominio
normadas aqui (djen-backup, contratos de query, fronteira CSS
Panda/Svelte) e tocada pelo trabalho desta rodada, que e
infraestrutura de deploy (relays HTTP e DJEN proxy) e sua cobertura de
teste em tres runtimes (Python/pytest, JS/vitest, Go/go test). A
secao "Antes de committing" (`ruff check`, `ruff format --check`,
`pytest -q`) se aplica ao lado Python e foi seguida integralmente;
os equivalentes em JS (`npm test`) e Go (`go vet`, `go test`) foram
seguidos pelas mesmas razoes.
