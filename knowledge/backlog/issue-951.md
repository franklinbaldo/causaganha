---
type: BacklogItem
issue_number: 951
title: "web(agentes): criar entrada pública para usar o CausaGanha via MCP"
category: "infra_decision"
blocking_reason: "The local/stdio slice is already shipped (see issue body checklist: #979/#982/#996). Only the remote HTTP CTA/config on /agentes remains, and that depends entirely on issue #950's rollout (live URL + smoke proof), which has not happened."
unblock_condition: "Issue #950 produces a stable public URL + passing smoke (mcp-rollout-proof.json); only then should web/src/pages/agentes.astro gain an HTTP config snippet."
last_verified_run_id: "2026-09-25-exciting-mccarthy-orr2e3"
last_verified_at: "2026-09-25T23:45:00Z"
status: "blocked"
---

# Issue #951: web(agentes): criar entrada pública para usar o CausaGanha via MCP

The local/stdio slice is already shipped (#979/#982/#996). Only the remote HTTP path is blocked, on issue #950.

**Para desbloquear:** wait for issue #950's live rollout (see `knowledge/backlog/issue-950.md`).

**Nota (2026-09-25, rodada `orr2e3`):** `#950` havia sido fechada indevidamente em 2026-09-25 (ver nota em `issue-950.md`) sem que o rollout remoto tivesse de fato ocorrido; reaberta nesta rodada. `web/src/pages/agentes.astro` continua correto ao dizer "Remoto ainda não é oficial" — nenhuma mudança de código necessária aqui, só a reconciliação deste backlog com o estado real de `#950`.
