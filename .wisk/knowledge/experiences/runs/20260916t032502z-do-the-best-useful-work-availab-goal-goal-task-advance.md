---
goal: "Add CI coverage for deployment/archive-cors-proxy (the Worker that fixes issue #1482's CORS block for DuckDBExplorer.svelte's read_parquet), so a regression in its allow-list regexes or CORS headers can't merge silently."
id: "run-goals/20260916t032502z-do-the-best-useful-work-availab/goal-task-advance"
kind: "task-advance"
rationale: "Issue #1471/#1472 (the active handoff) and #1482's own deploy step remain blocked on missing credentials (IA_ACCESS_KEY/IA_SECRET_KEY, Cloudflare) in this environment, confirmed again this round. deployment/archive-cors-proxy is the actual shipped fix path for #1482 (wired into web/src/pages/explorador.astro via PUBLIC_ARCHIVE_PROXY_BASE / archiveProxyBase.ts) with a real 15-case Vitest suite (PR #1521) that needs zero Cloudflare credentials to run (workerd sandbox), yet no workflow under .github/workflows/ ever runs it or its wrangler dry-run bundle check -- a genuine, non-credential-gated CI gap on real product code."
run: "runs/20260916T032502Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "A new failing test (tests/test_archive_cors_proxy_ci_coverage.py) demonstrating the gap goes RED against unmodified .github/workflows/test.yml, then GREEN after adding an archive-cors-proxy CI job that runs npm test + npm run check; full repo pytest/ruff and web suites stay green."
type: "RunGoal"
---

# RunGoal
