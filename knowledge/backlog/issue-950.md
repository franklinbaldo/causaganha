---
type: BacklogItem
issue_number: 950
title: "product(mcp): disponibilizar endpoint remoto read-only sem exigir clone local"
category: "infra_decision"
blocking_reason: "Requires a live, authenticated Cloud Run deploy of .github/workflows/deploy-mcp.yml (workload identity/service account) that an unattended round has no credentials to perform. All code/artifact prerequisites have been merged to main since 2026-09-04; only the operational rollout + smoke proof (mcp-rollout-proof.json) remain."
unblock_condition: "A session or the repo owner runs the deploy-mcp.yml workflow_dispatch with authorized GCP credentials, obtains a stable public URL, and the smoke step against processo_consultar + a product search tool passes."
last_verified_run_id: "2026-09-26-exciting-mccarthy-uz8msx"
last_verified_at: "2026-09-26T00:40:00Z"
status: "blocked"
---

# Issue #950: product(mcp): disponibilizar endpoint remoto read-only sem exigir clone local

Requires a live, authenticated Cloud Run deploy of `.github/workflows/deploy-mcp.yml` that an unattended round has no credentials to perform.

**Para desbloquear:** run `deploy-mcp.yml` via `workflow_dispatch` with authorized GCP Workload Identity/service account, then verify the resulting `mcp-rollout-proof.json` and public URL.

**Nota (2026-09-25, rodada `orr2e3`):** a issue havia sido fechada em 2026-09-25T10:15:17Z (PR #1630) por citar o merge de #1629, que só fechou o sub-item TM-06 (rate limiting) do threat model — não o rollout em si. Confirmado ao vivo que `deploy-mcp.yml` tem `0` execuções (`list_workflow_runs`). Issue reaberta no GitHub com comentário explicativo; este arquivo de backlog permanece `status: blocked` pela mesma razão operacional já diagnosticada por rodadas anteriores (2026-09-01 a 2026-09-07), agora apenas revalidada.

**Nota (2026-09-26, rodada `uz8msx`):** a issue foi refechada automaticamente pelo próprio merge da PR de correção anterior (#1661) — o título continha a frase "closed #950", que o GitHub trata como closing keyword (sinônimo de "closes #950"), então o merge reclosed a issue no mesmo instante em que a PR pretendia documentá-la como reaberta. Reaberta de novo nesta rodada, desta vez com o cuidado deliberado de não incluir nenhum closing keyword seguido de `#950` em título/corpo/commits do PR desta rodada. `deploy-mcp.yml` continua com `0` execuções; nenhuma mudança na fronteira operacional (credenciais GCP ausentes nesta sessão).
