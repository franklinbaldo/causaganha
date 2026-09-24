---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-p973xb-reading-claude-md"
run_id: "2026-09-24-exciting-mccarthy-p973xb"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Releitura integral no inicio da rodada. Sem mudanca de conteudo desde a ultima leitura registrada (i23hxr, mais cedo em 2026-09-24). Confirma: sync-manifest.parquet como fonte da verdade do djen-backup, djen_raw como codigo de transporte (nunca veredito de disponibilidade), 403 nunca e absent, fronteira de tokens CSS Panda/Svelte (tres ilhas legadas usam --papel-*/--s-*, novas paginas usam css()/recipes), regras de estilo Python (ruff estrito, TRY300/TRY301/TRY401, sem except Exception generico fora do bulkhead da ADR 0011, from __future__ import annotations). Nao menciona Wisk/AgentRun -- essa tensao vive em .claude/hourly-loop.md (arquivo separado, ver reading-okf). O trabalho selecionado nesta rodada (neutralizar formula injection na exportacao CSV, issue #1612, em web/src/components/PublicationSearch.svelte) e frontend TypeScript/Svelte, fora do escopo Python do CLAUDE.md, mas nao conflita com nenhuma regra aqui -- nao introduz custom property CSS nova nem toca a fronteira Panda/Svelte."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no inicio da rodada, conforme
exigido pelo contrato `AgentRun`. Nenhuma mudanca relevante desde a
ultima rodada que o leu. O trabalho selecionado nesta rodada e
frontend (neutralizacao de formula injection na exportacao CSV,
issue #1612) e nao toca nenhuma das areas normadas por este arquivo
(djen-backup, contratos de query, fronteira CSS Panda/Svelte, estilo
Python) alem de "antes de commitar" (ruff/pytest), que nao se aplica
diretamente a mudanca TS mas cujo equivalente (lint/typecheck/test do
`web/`) foi seguido.
