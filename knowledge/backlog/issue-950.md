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

**Nota 2 (2026-09-26, mesma rodada `uz8msx`):** a lição acima não foi suficiente. A PR que registrou essa correção (#1663) refechou a issue de novo no próprio merge — seu corpo, ao *explicar* o bug anterior, citou a frase-problema entre aspas para descrevê-la. O parser de closing keyword do GitHub não entende aspas/markdown de citação: ele casou o mesmo padrão dentro da citação e fechou a issue de novo, no ato de documentar por que isso não devia acontecer. Reaberta pela terceira vez. Lição corrigida: nenhum PR/commit que precise falar sobre esse bug específico deve escrever a combinação de uma dessas palavras (close/closes/closed/fix/fixes/fixed/resolve/resolves/resolved, em qualquer capitalização) imediatamente seguida de `#950` — nem mesmo entre aspas para citar o problema. Quando for necessário mencionar essa combinação problemática, escrever o número sem o `#` (ex.: "issue 950" ou "issue número novecentos e cinquenta") e usar a URL completa (`https://github.com/franklinbaldo/causaganha/issues/950`) para a referência cruzada real. Este próprio arquivo markdown não corre esse risco (não é título/corpo/commit de PR, então o GitHub não o escaneia), mas qualquer PR/commit que cite este arquivo ou resuma esta nota precisa aplicar a mesma cautela.
