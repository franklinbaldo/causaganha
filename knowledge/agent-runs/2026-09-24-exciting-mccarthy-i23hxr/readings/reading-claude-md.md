---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-i23hxr-reading-claude-md"
run_id: "2026-09-24-exciting-mccarthy-i23hxr"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Confirma o modelo mental do djen-backup (sync-manifest.parquet fonte da verdade, djen_raw!=veredito de disponibilidade, 403 nunca e absent), a fronteira de tokens CSS Panda/Svelte, e as regras de estilo Python (ruff estrito, sem except Exception generico fora do bulkhead da ADR 0011). Nenhuma mudanca de conteudo desde a ultima rodada que leu este arquivo (khpkk2, 2026-09-24). CLAUDE.md nao menciona Wisk/AgentRun -- essa politica de runtime vive em .claude/hourly-loop.md, arquivo separado (ver reading-okf). Nada aqui conflita com o trabalho selecionado nesta rodada (correcao de achados reais do segmenter_semantic_audit.py sobre #1050), que cai inteiramente sob as regras de estilo e 'antes de commitar' ja descritas."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no inicio da rodada, conforme
exigido pelo contrato `AgentRun`. Sem mudancas relevantes desde a
ultima rodada que o leu (`khpkk2`). A arquitetura djen-backup, os
contratos de query do frontend, a fronteira de tokens CSS Panda/Svelte
e as regras de estilo Python (ruff estrito, TRY300/TRY301/TRY401,
`from __future__ import annotations`) permanecem como descritas e
foram seguidas no trabalho desta rodada.
