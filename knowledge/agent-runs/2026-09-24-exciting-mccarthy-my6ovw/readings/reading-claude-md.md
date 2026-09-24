---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-my6ovw-reading-claude-md"
run_id: "2026-09-24-exciting-mccarthy-my6ovw"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces (Python backend src/causaganha + src/djen_backup; web/ Astro+Svelte). The djen-backup sync engine's sync-manifest.parquet on IA is the single source of truth for coverage; djen_raw is a raw HTTP status code, never a verdict -- a 200 with body 'Sem comunicacoes' (no download URL) is absent, same as 404. None of this round's selected work touches djen-backup, so these correctness rules are read for context but not directly exercised. The Style section requires ruff-strict code (no blind except Exception outside the ADR-0011 worker-loop-bulkhead pattern, TRY300/301/401 enforced) and 'uv run ruff check'/'ruff format --check'/'uv run pytest -q' green before committing -- these gates apply to any script this round touches (segmenter ingestion scripts)."
---

# Leitura: CLAUDE.md
