---
type: AgentEvidence
id: "2026-09-11-exciting-mccarthy-qpktqe-evidence-juris-green"
run_id: "2026-09-11-exciting-mccarthy-qpktqe"
goal_id: "2026-09-11-exciting-mccarthy-qpktqe-goal-juris-url-percent-encoding-mismatch"
kind: "test_green"
reference: "scripts/reconcile_processos.py::fetch_juris_from_ia; tests/test_reconcile_processos.py::test_fetch_juris_from_ia_matches_published_juris_url_encoding"
summary: "fetch_juris_from_ia now wraps the filename in urllib.parse.quote() before building the stored URL, matching causaganha.decisoes.published._juris_url's convention exactly. `list(urls.values()) == [expected_url]` passes. Full tests/test_reconcile_processos.py (all tests), tests/causaganha/decisoes/, and tests/causaganha_mcp/ suites pass -- no regression from the encoding change, since the pre-existing _mock_juris_remote fixture's ASCII-only filenames ('2024-01-ACORDAO.parquet', '2024-02-SENTENCA.parquet') are unaffected by quote() (percent-encoding an already-ASCII-safe string is a no-op). `uv run ruff check`/`ruff format --check` clean on both changed files. Full repo-wide `uv run pytest -q` green except this round's own draft run.md completeness gate (expected while completed_at is still empty, per the scaffold's own documented allowance)."
---

# GREEN: fetch_juris_from_ia percent-encoda o nome do arquivo

Após envolver o nome do arquivo em `quote()`, a URL armazenada bate exatamente com a de `published.discover_published_juris_datasets`. Suítes relacionadas e `ruff` limpos; suíte completa do repositório verde (exceto o próprio rascunho deste `run.md`, esperado).
