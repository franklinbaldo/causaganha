---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-1c8jcc-reading-claude-md"
run_id: "2026-09-24-exciting-mccarthy-1c8jcc"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Leitura integral no inicio da rodada. Confirma o essencial ja estabelecido por rodadas anteriores da mesma janela (2026-09-24): sync-manifest.parquet como fonte da verdade do djen-backup, djen_raw como codigo de transporte HTTP (nunca veredito de disponibilidade, 200-sem-URL e absent), 403 nunca e absent, a fronteira Panda/Svelte (tres ilhas legadas usam --papel-*/--s-*, paginas novas usam css()/recipes), e as regras de estilo Python (ruff estrito, TRY300/TRY301/TRY401, sem except Exception generico fora do bulkhead da ADR 0011, from __future__ import annotations). O trabalho selecionado nesta rodada (eliminar 'eval' e interpolacao insegura de workflow_dispatch em workflows do GitHub Actions com secrets -- issue #1608, TM-01 do threat model) e infraestrutura CI/CD (.github/workflows/*.yml) mais testes Python novos em tests/ -- fora das areas de dominio normadas por este arquivo, mas 'Antes de committing' (ruff check/format --check/pytest) se aplica integralmente e foi seguido."
---

# Leitura: CLAUDE.md

Leitura integral do guia do projeto no inicio da rodada, conforme
exigido pelo contrato `AgentRun`. Nenhuma das areas de dominio
normadas aqui (djen-backup, contratos de query, fronteira CSS
Panda/Svelte) e tocada pelo trabalho desta rodada, que e puramente
infraestrutura de CI (workflows GitHub Actions) e sua cobertura de
teste Python. A secao "Antes de committing" (`ruff check`,
`ruff format --check`, `pytest -q`) se aplica e foi seguida
integralmente.
