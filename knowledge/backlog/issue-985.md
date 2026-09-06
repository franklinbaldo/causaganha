---
type: BacklogItem
issue_number: 985
title: "data(tse): provar integração mínima do dataset Processual 2026"
category: "network_access"
blocking_reason: "Requires live read access to TSE's official ZIPs (src/tse_processual/catalog.py resources, host cdn.tse.jus.br) to profile schema/identity/joins and compare against DataJud, per the issue's own evidence-first plan. This session verified live: DNS resolves and TCP connects to cdn.tse.jus.br and dadosabertos.tse.jus.br (unlike prior sessions, which failed outright at DNS resolution), but every path tested — the three admitted resource URLs, the bare /estatistica/sead/ directory, and the dadosabertos CKAN API — returns HTTP 403 with an Akamai edgesuite.net 'Access Denied' body (confirmed via response body, not just status code), reproducible with and without browser-like User-Agent/Referer/Range headers and via a real headless-Chromium navigation (net::ERR_CONNECTION_RESET). This is a network/WAF-level rejection of the whole domain from this runtime's egress, not a credentials gap: the acquisition/inspection/profiling code (src/tse_processual/acquisition.py, inspection.py, profiling.py) is already written, reviewed and merged on main, and needs no further implementation to run the moment a request from this host is not rejected."
unblock_condition: "A session whose egress is not rejected by TSE's Akamai front (e.g. a Brazil-based runner, or one on an allow-listed range) can execute scripts/inspect_tse_processual.py / scripts/profile_tse_processual.py against the three official ZIPs and attach the resulting report to the issue. Absent that, the repo owner supplying pre-fetched copies of the three ZIPs (with their official URL/date/checksum) would let a future round run the already-merged profiler directly."
last_verified_run_id: "2026-09-06-exciting-mccarthy-589obm"
last_verified_at: "2026-09-06T19:30:00Z"
status: "blocked"
---

# Issue #985: data(tse): provar integração mínima do dataset Processual 2026

Requires live read access to TSE's official ZIPs (`src/tse_processual/catalog.py` resources, host `cdn.tse.jus.br`) to profile schema/identity/joins and compare against DataJud, per the issue's own evidence-first plan.

This is **not** an Internet Archive upload-credentials blocker (that reason belongs to #1011/#1022, a different issue about publishing TCU data). #985 has not reached an IA-upload step; it is stuck earlier, at reading the TSE source data.

Verified live this round: DNS now resolves and TCP connects to `cdn.tse.jus.br`/`dadosabertos.tse.jus.br` (prior sessions failed outright at DNS resolution). But every path tested — the three admitted resource URLs, the bare `/estatistica/sead/` directory, and the CKAN API — returns HTTP 403 with an Akamai `edgesuite.net` "Access Denied" body, reproducible with browser-like headers and via a real headless-Chromium navigation. This reads as a network/WAF-level rejection of the whole domain from this runtime's egress, not a per-file or bot-fingerprint block, and not a credentials gap: the acquisition/inspection/profiling code is already merged on `main` and needs no further implementation.

**Para desbloquear:** a session whose egress is not rejected by TSE's Akamai front (e.g. a Brazil-based runner) running `scripts/inspect_tse_processual.py` / `scripts/profile_tse_processual.py` against the three official ZIPs, or the repo owner supplying pre-fetched copies of them.
