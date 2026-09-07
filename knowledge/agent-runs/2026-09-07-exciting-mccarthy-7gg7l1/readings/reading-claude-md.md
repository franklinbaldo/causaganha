---
type: AgentReading
id: "2026-09-07-exciting-mccarthy-7gg7l1-reading-claude-md"
run_id: "2026-09-07-exciting-mccarthy-7gg7l1"
subject: "claude_md"
reference: "/home/user/causaganha/CLAUDE.md, full file, read at session start"
finding: "Nothing in the current diff (there is none) touches djen_raw/djen_status semantics, the IA upload byte-reading contract, or the Panda/Svelte CSS boundary, so those rules are not directly exercised this round. The applicable section is 'Before committing' (ruff check, ruff format --check, pytest -q) as the gate for the docs-only knowledge/ changes this round makes, plus the general instruction to verify recorded-but-unconfirmed facts against live DJEN/IA state before trusting them — the same standard this round applied to the backlog cache's credential/infra/network claims instead of DJEN specifically."
---

# Leitura de CLAUDE.md

Nenhuma regra específica de `djen_backup`/CSS foi exercida nesta rodada (sem mudança de código de produto). O gate aplicável é o checklist "Before committing", e o princípio geral de "verificar contra fonte ao vivo antes de confiar em um estado registrado" foi aplicado ao cache de backlog em vez de aos dados DJEN.
