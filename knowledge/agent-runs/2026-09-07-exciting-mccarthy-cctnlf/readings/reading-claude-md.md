---
type: AgentReading
id: "2026-09-07-exciting-mccarthy-cctnlf-reading-claude-md"
run_id: "2026-09-07-exciting-mccarthy-cctnlf"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Re-read in full at round start. Key correctness rules that must gate any work this round: djen_raw is transport-only (HTTP status), never a verdict — availability requires HTTP 200 AND a download URL in the body, a 200-without-URL ('Sem comunicações') is absent exactly like 404; 403 must never be treated as absent (CloudFront/WAF rate-limit); djen_raw='200'+djen_status='available' is not self-consistent proof on its own (historical ~79K-row bug, now fixed by promoting the corrected sync-manifest.parquet as sole source of truth per docs/planning/manifest-source-of-truth.md, which this round independently verified reads 'Fase 3 ✅ (2026-07-08, PR #800)' — the legacy CSV fallback is fully retired, not just planned). CSS token boundary: new work must use Panda css()/recipes, never invent bespoke custom properties; the four named legacy Svelte islands keep their --papel-*/--s-* names. Style: ruff strict, no blind except Exception, TRY300/TRY301/TRY401, Python 3.12+ with `from __future__ import annotations`. Before committing: ruff check, ruff format --check, pytest -q. No decision this round changes djen_raw/djen_status semantics, IA upload internals, or the CSS token split, so no direct conflict was found between planned work and CLAUDE.md's hard rules; this reading is the reference point for judging future work as it's selected."
---

# Leitura de CLAUDE.md

Releitura completa no início da rodada. Regras de correção mais relevantes para qualquer trabalho futuro nesta sessão: `djen_raw` é só transporte (nunca veredito), `djen_status` deriva de status+corpo, 403 nunca é ausência, e o bug histórico de ~79K linhas já foi corrigido (Fase 3 do plano de fonte-da-verdade confirmada concluída em 2026-07-08). Fronteira CSS: Panda `css()`/recipes para código novo; os quatro ilhas Svelte legadas mantêm `--papel-*`/`--s-*`. Estilo: ruff estrito, sem `except Exception` genérico, TRY300/TRY301/TRY401. Gates antes de commit: `ruff check`, `ruff format --check`, `pytest -q`.
