---
type: AgentReading
id: "2026-09-08-exciting-mccarthy-5pmmrp-reading-claude-md"
run_id: "2026-09-08-exciting-mccarthy-5pmmrp"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Re-read CLAUDE.md in full. Key invariants for this round: djen_raw is the raw HTTP status, never a verdict on availability; a 200 with body 'Sem comunicações' (no download URL) is absent, same as 404 -- never conflate djen_raw='200' with djen_status='available'. 403 must never be treated as absent (CloudFront/WAF rate-limiting). Per-item lock + token bucket for IA uploads must stay; ItemBusyError re-queues. Rate-limit observer updates throttled to 2Hz because manifest.counts() scans 157K entries. CSS: Panda via the cobogo preset is the one design system; the three legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations) keep --papel-*/--s-* aliases, no new bespoke custom properties, and Svelte components never call css() directly (Panda's include never scans .svelte). Style: ruff strict, no blind except Exception outside the documented per-item worker-loop bulkhead pattern (ADR 0011), TRY300/TRY301/TRY401 enforced, Python 3.12+ with future annotations. Before committing: ruff check, ruff format --check, pytest -q. Nothing in CLAUDE.md itself changed since the last round's reading (obl3ux); still the same file map and rules of the road."
---

# Leitura do CLAUDE.md

Nenhuma mudança relevante desde a última rodada. Reforcei os invariantes de djen_raw/djen_status, a fronteira de tokens CSS (Panda + três ilhas Svelte legadas) e as regras de estilo (ruff estrito, bulkhead ADR-0011) antes de escolher trabalho nesta rodada.
