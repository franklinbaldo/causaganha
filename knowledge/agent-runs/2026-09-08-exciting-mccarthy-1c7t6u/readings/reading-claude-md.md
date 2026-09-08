---
type: AgentReading
id: "2026-09-08-exciting-mccarthy-1c7t6u-reading-claude-md"
run_id: "2026-09-08-exciting-mccarthy-1c7t6u"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Read in full at round start. Key facts reconfirmed: sync-manifest.parquet on IA is the sole source of truth; djen_raw is a bare HTTP transport code and must never be treated as a verdict -- availability requires HTTP 200 and a download URL in the body, since a 200-without-URL is absent exactly like 404; 403 must never be treated as absent; ~79K legacy rows in the retired sync-manifest.csv conflated bare-200 with available and were never backfilled. CSS: one design system (Panda via the cobogo preset); index.css is a compatibility bridge for three legacy Svelte islands only. Style: ruff strict, no blind except Exception, TRY300/301/401 enforced. This matches the recent merged PRs in git log (backfill_probe body-vs-status classification, several absent/unknown classification fixes) -- the CLAUDE.md rules are being actively enforced by recent rounds, not just documentation debt. Also spotted a gap worth flagging for a future round (see this run's next_move): the 'No blind except Exception' claim isn't actually enforced by ruff's BLE001 for handlers that call .exception(...) inside the except block -- found while an Explore subagent scanned candidates for this round's goal."
---

# Reading: CLAUDE.md

Releitura completa. Regras de correção do djen_backup confirmadas e vigentes. Encontrado, via o subagente Explore desta rodada, um gap na afirmação sobre `except Exception` + BLE001 (ver `next_move` do `run.md`), não selecionado como o goal desta rodada.
