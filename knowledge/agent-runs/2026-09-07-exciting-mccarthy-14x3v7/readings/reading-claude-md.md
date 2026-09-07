---
type: AgentReading
id: "2026-09-07-exciting-mccarthy-14x3v7-reading-claude-md"
run_id: "2026-09-07-exciting-mccarthy-14x3v7"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Re-read in full at round start (loaded verbatim into this session's system prompt). Hard correctness rules that gate any djen_backup work this round: djen_raw is the transport-only HTTP status code (never a verdict on availability); djen_status is derived from the full response (status + body); availability requires HTTP 200 AND a download URL in the body — a 200-without-URL ('Sem comunicações') is absent exactly like 404/400. 403 must never be treated as absent (CloudFront/WAF rate-limiting). Verified src/djen_backup/djen.py's get_caderno_url still implements this contract correctly line-by-line (404/400 -> DJENNotFoundError, 403 -> DJENRateLimitedError, 200-without-url body 'Sem comunicações' -> DJENNotFoundError(200)) — no regression since the last round's reading. Style rules applied to any diff this round: ruff strict (BLE/TRY families extend-selected in ruff.toml), no blind except Exception unless per-file-ignored (only src/stj_acordaos/__main__.py carries a BLE001 ignore), TRY300/TRY301/TRY401 enforced, Python 3.12+ with `from __future__ import annotations`. Pre-commit gates: ruff check, ruff format --check, pytest -q. Also re-read the CSS token boundary section (Panda vs the four legacy Svelte islands) since this round's goal search extended into web/ — relevant if any frontend work is selected."
---

# Leitura de CLAUDE.md

Releitura completa no início da rodada. As regras de correção mais críticas (403 nunca é ausência; 200 sem URL de download é ausência) foram verificadas linha a linha contra `src/djen_backup/djen.py` e continuam corretamente implementadas — sem regressão desde a última rodada. Nenhum conflito encontrado entre essas regras e o trabalho considerado nesta rodada.
