---
type: AgentReading
id: "2026-09-07-exciting-mccarthy-vgrupn-reading-claude-md"
run_id: "2026-09-07-exciting-mccarthy-vgrupn"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Re-read in full at round start (already loaded verbatim into this session's system prompt). Hard correctness rules that gate any djen_backup work this round: djen_raw is the transport-only HTTP status code (never a verdict); djen_status is derived from status+body; availability requires HTTP 200 AND a download URL in the body — a 200-without-URL ('Sem comunicações') is absent exactly like 404/400. Most directly relevant to this round's selected work: '403 must never be treated as absent — CloudFront/WAF returns 403 when rate-limiting; genuine absent is 404, 400, or 200-without-URL only.' This is precisely the invariant src/djen_backup/probe.py's _probe_one was violating (see goal-probe-403-rate-limit.md): it had no handling at all for the 403 case (DJENRateLimitedError), unlike engine.py's checker and scripts/drain_unknowns.py which both explicitly catch it and skip-not-mark. Style rules applied to this round's diff: ruff strict, no blind except Exception (BLE001), TRY300/TRY301/TRY401, Python 3.12+ with `from __future__ import annotations`. Pre-commit gates: ruff check, ruff format --check, pytest -q. No decision this round touches djen_raw/djen_status semantics, IA upload internals, or the CSS token boundary, so no conflict was found between the selected work and CLAUDE.md's hard rules."
---

# Leitura de CLAUDE.md

Releitura completa no início da rodada. A regra mais diretamente relevante para o trabalho desta rodada: **403 nunca é ausência** — é bloqueio transitório de CloudFront/WAF, deve ser ignorado e reprocessado na próxima rodada, nunca marcado como `absent`. Esse é exatamente o invariante que `src/djen_backup/probe.py` violava silenciosamente (ver `goal-probe-403-rate-limit.md`).
