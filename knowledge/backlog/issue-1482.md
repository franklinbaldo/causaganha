---
type: BacklogItem
issue_number: 1482
title: "web(duckdb): archive.org file-download endpoint sends no CORS header — DuckDBExplorer's read_parquet() may be unreadable cross-origin"
category: "credentials"
blocking_reason: "The code-level workaround (a narrow Cloudflare Worker proxy that re-serves archive.org/download/djen-*/*.parquet with Access-Control-Allow-Origin added, forwarding Range/Content-Range) is already implemented and merged in #1521 (deployment/archive-cors-proxy/, web/src/lib/archiveProxyBase.ts, PUBLIC_ARCHIVE_PROXY_BASE prop on DuckDBExplorer.svelte). The issue's own 'Suggested next step' #3 (a dedicated live-network Playwright job in CI so a future CORS-behavior change is caught automatically) is also already done: .github/workflows/archive-cors-probe.yml runs scripts/benchmarks/archive_cors_probe.py against live archive.org on a weekly cron plus workflow_dispatch. What remains is deploying the Cloudflare Worker for real and setting PUBLIC_ARCHIVE_PROXY_BASE in the dashboard's build environment -- this session's environment was checked (`env | grep -iE 'cloudflare|cf_api|CLOUDFLARE'`) and has no Cloudflare API token/account credentials. Until deployed, nothing changes for users: read_parquet() still targets archive.org directly and the existing CORS-block classification/messaging in DuckDBExplorer.svelte stays accurate."
unblock_condition: "A session whose environment has real Cloudflare deploy credentials (the token/account id `npx wrangler deploy` from deployment/archive-cors-proxy/ needs), to run the actual deploy, then set PUBLIC_ARCHIVE_PROXY_BASE to the deployed Worker's URL in the dashboard's build environment and confirm one real DuckDBExplorer query against the published dataset through the proxy."
last_verified_run_id: "2026-09-17-exciting-mccarthy-726qh5"
last_verified_at: "2026-09-17T02:35:00Z"
status: "blocked"
---

# Issue #1482: web(duckdb): archive.org file-download endpoint sends no CORS header

Todo trabalho de codigo alcancavel sem credenciais de deploy ja esta
implementado e mesclado: o proxy Cloudflare Worker (#1521) e a probe
real de browser agendada em CI (`.github/workflows/archive-cors-probe.yml`,
ja fechando a sugestao #3 do proprio issue). O unico passo restante e
o deploy real do Worker (`npx wrangler deploy` em
`deployment/archive-cors-proxy/`, ja validado com `--dry-run` em rodada
anterior) e a configuracao de `PUBLIC_ARCHIVE_PROXY_BASE` no ambiente
de build do dashboard -- ambos exigem credenciais Cloudflare que este
ambiente nao tem.

**Para desbloquear:** uma sessao cujo ambiente tenha credenciais reais
de deploy Cloudflare (o token/account id que `npx wrangler deploy`
exige).
