---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-e3tk18-reading-claude-md"
run_id: "2026-09-24-exciting-mccarthy-e3tk18"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Releitura integral do guia do projeto. Confirma o modelo mental do djen-backup (sync-manifest.parquet fonte da verdade, djen_raw!=veredito de disponibilidade, 403 nunca e absent), a fronteira de tokens CSS Panda/Svelte, e as regras de estilo Python (ruff estrito, TRY300/TRY301/TRY401, sem except Exception generico fora do bulkhead da ADR 0011, from __future__ import annotations). Nenhuma mudanca de conteudo desde a ultima rodada que leu este arquivo nesta mesma janela (i23hxr, 2026-09-24). CLAUDE.md nao menciona Wisk/AgentRun -- essa politica de runtime vive em .claude/hourly-loop.md, arquivo separado (ver reading-okf). Nada aqui conflita com o trabalho selecionado nesta rodada (fechar o ponto cego de teste remanescente em scripts/segmenter_semantic_audit.py e corrigir um bug real de deteccao morta que ele escondia), que cai inteiramente sob as regras de estilo e 'antes de commitar' ja descritas (ruff check/format --check, pytest -q)."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no inicio da rodada, conforme
exigido pelo contrato `AgentRun`. Sem mudancas relevantes desde a
ultima rodada que o leu nesta mesma janela (`i23hxr`). A arquitetura
djen-backup, os contratos de query do frontend, a fronteira de tokens
CSS Panda/Svelte e as regras de estilo Python permanecem como
descritas e foram seguidas no trabalho desta rodada.
