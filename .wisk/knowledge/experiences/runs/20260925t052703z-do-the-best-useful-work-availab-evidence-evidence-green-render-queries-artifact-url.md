---
type: "RunEvidence"
id: "run-evidence/20260925t052703z-do-the-best-useful-work-availab/evidence-green-render-queries-artifact-url"
run: "runs/20260925T052703Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "uv run pytest -q tests/test_render_queries.py (after the fix); uv run ruff check/format --check scripts/render_queries.py tests/test_render_queries.py"
summary: "GREEN: both new tests pass after scripts/render_queries.py::_register_comunicacoes validates each arquivo_ia_url via causaganha.processos.service._validate_artifact_url (imported, same pattern already used in this file for tjro_juris.service._PARQUET_SCHEMA) before interpolating into read_parquet([...]) -- invalid URLs (wrong host, embedded quote) are dropped with a WARNING print instead of reaching the SQL string; an all-invalid index still falls back to the catalog manifest. Full tests/test_render_queries.py: 56/56 green (54 pre-existing + 2 new). ruff check/format --check clean on both touched files."
---

# RunEvidence
