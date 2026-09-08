---
type: AgentReading
id: "2026-09-08-exciting-mccarthy-1c7t6u-reading-claude-md"
subject: "CLAUDE.md"
run_id: "2026-09-08-exciting-mccarthy-1c7t6u"
---

# Reading: CLAUDE.md

Read `/home/user/causaganha/CLAUDE.md` in full this round.

Key facts reconfirmed: `sync-manifest.parquet` on IA is the sole source of truth (event log + compactor); `djen_raw` is a bare HTTP transport code and must never be treated as a verdict — availability requires HTTP 200 **and** a download URL in the body, since a 200-without-URL ("Sem comunicações") is `absent` exactly like 404; 403 must never be treated as absent (CloudFront/WAF rate-limiting); ~79K legacy rows in the retired `sync-manifest.csv` conflated bare-200 with available and were never backfilled — don't trust apparent canonical-looking data without a live DJEN check. CSS: one design system (Panda via the `cobogo` preset); `index.css` is a compatibility bridge for three legacy Svelte islands only. Style: ruff strict, no blind `except Exception`, TRY300/301/401 enforced, Python 3.12+ `|` unions with `from __future__ import annotations`.

This matches the last several merged PRs in git log (#1334 backfill_probe body-vs-status classification, #1328/#1326/#1323/#1325 absent/unknown classification fixes) — the CLAUDE.md rules are being actively enforced by recent rounds, not just documentation debt.
