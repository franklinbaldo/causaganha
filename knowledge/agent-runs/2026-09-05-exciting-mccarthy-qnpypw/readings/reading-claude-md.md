---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-qnpypw-reading-claude-md"
run_id: "2026-09-05-exciting-mccarthy-qnpypw"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: djen-backup (src/djen_backup) with sync-manifest.parquet on IA as sole canonical source, and the web frontend (Astro 5 + Svelte 5) fed by .qmd query contracts rendered by scripts/render_queries.py. Correctness rules relevant to this round's chosen work (verifying issue #1042, the update-catalog/indice_processual end-to-end proof): djen_raw is a transport code, not an availability verdict (200-without-URL is absent); the manifest is the sole source of truth; before 'fixing' any available/absent discrepancy, verify live against DJEN — the same evidence-first discipline this round applied to #1042 (verify against a live workflow run and a live read-back before trusting a checklist as still-open). Python style: ruff strict, no blind except Exception, TRY300/TRY301/TRY401 enforced. This round made zero source changes (pure verification), so the only gate exercised was confirming `uv run ruff check`, `uv run ruff format --check` and `uv run pytest -q` stayed green with only knowledge/ docs added."
---

# Leitura de CLAUDE.md

Regras de correção do manifesto (djen_raw != veredito) e disciplina de verificação ao vivo antes de aceitar um estado registrado como correto — exatamente o padrão aplicado nesta rodada para fechar a #1042 com prova real em vez de assumir o histórico da issue.
