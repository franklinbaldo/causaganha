---
type: AgentReading
id: "2026-09-09-exciting-mccarthy-v38h6d-reading-claude-md"
run_id: "2026-09-09-exciting-mccarthy-v38h6d"
subject: "CLAUDE.md"
reference: "/home/user/causaganha/CLAUDE.md"
finding: "Confirmed the correctness rules that recur across today's fix lineage: djen_raw is a transport code (HTTP status), never a verdict on availability -- djen_status must be derived from status+body, and a 200-without-download-URL body ('Sem comunicações') is absent, same as 404/400. 403 must never be read as absent (CloudFront/WAF rate-limiting). sync-manifest.parquet is the sole source of truth; sync-manifest.csv is a derived export nothing reads. New frontend datasets go through .qmd query contracts in web/src/queries/ plus a Zod schema + registry entry in web/src/lib/data/contracts.ts -- never ad-hoc cache generation. Style: ruff strict, no blind except Exception (specific types, or the per-item worker-pool bulkhead pattern from ADR-0011 with .exception() logged), TRY300/301/401 enforced, Python 3.12+ with `from __future__ import annotations`. CSS: Panda via the cobogo preset is the only design system; only three legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations) still use --papel-*/--s-* aliases, and Panda's `include` never scans .svelte files so raw css() calls inside .svelte are unreliable. Pre-commit gate: ruff check, ruff format --check, pytest -q."
---

# CLAUDE.md reading

See `finding` in frontmatter. No open questions -- this file is unchanged from every prior 2026-09-09 round's reading of it (confirmed by diffing against the readings embedded in knowledge/agent-runs/2026-09-09-exciting-mccarthy-qvqmci/).
