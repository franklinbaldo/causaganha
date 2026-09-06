---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-nao666-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-nao666"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: djen-backup sync engine (sync-manifest.parquet on IA is the sole source of truth; djen_raw is a transport code, not an availability verdict — 200-without-download-URL is absent, same as 404) and the web frontend fed by .qmd query contracts. Correctness rules most relevant this round: never treat 403 as absent; don't trust djen_raw=200+djen_status=available as self-consistent without live verification (historical ~79K false positives); the CSS token boundary keeps Brazilian-Modernism tokens (--s-*, --papel-*, --tinta-*) out of container-layout data pages, semantic tokens (--color-*, --space-*) in. Before committing: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. This round's selected work (verifying and closing a stale meta-review issue, #924, using only read-only live checks — HTTP GET on a public IA-hosted JSON manifest, grep/read against already-merged code, no writes to djen-backup state, no CSS/web changes) does not touch any of CLAUDE.md's named invariants (manifest correctness, IA upload mechanics, CSS token lanes) — the only gate that applies is the standard ruff/pytest check before pushing the OKF report commit."
---

# Leitura de CLAUDE.md

Nenhuma regra de correção do manifesto DJEN, de upload IA ou de fronteira CSS é tocada pelo trabalho desta rodada (triagem/fechamento da issue #924 com evidência ao vivo, sem mudança de código de produto). O único gate que se aplica é o padrão de pre-commit (ruff + pytest) sobre o próprio commit do relatório OKF.
