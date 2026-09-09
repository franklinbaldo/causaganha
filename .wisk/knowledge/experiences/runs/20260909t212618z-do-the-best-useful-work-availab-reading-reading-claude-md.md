---
type: "RunReading"
id: "run-readings/20260909t212618z-do-the-best-useful-work-availab/reading-claude-md"
run: "runs/20260909T212618Z-do-the-best-useful-work-available-in-this-reposi"
kind: "claude-md"
subject: "CLAUDE.md"
reference: "CLAUDE.md"
finding: "djen_raw is the raw HTTP status transport code, not a verdict; djen_status is derived and must treat 200-with-no-download-URL ('Sem comunicacoes') as absent, same as 404/400. Never treat 403 as absent (CloudFront/WAF rate-limit). Ruff strict, no blind except Exception outside documented per-item worker bulkheads (ADR-0011). Manifest is the sole source of truth; .qmd contracts render to web/public/data via scripts/render_queries.py."
---

# RunReading
