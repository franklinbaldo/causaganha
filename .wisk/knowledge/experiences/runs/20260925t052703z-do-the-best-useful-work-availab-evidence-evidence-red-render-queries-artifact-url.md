---
type: "RunEvidence"
id: "run-evidence/20260925t052703z-do-the-best-useful-work-availab/evidence-red-render-queries-artifact-url"
run: "runs/20260925T052703Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "uv run pytest -q tests/test_render_queries.py -k artifact_policy (before the fix)"
summary: "RED confirmed live: test_register_comunicacoes_discards_url_that_fails_artifact_policy failed with duckdb.ParserException: syntax error at or near ';' -- the quote-injection fixture ''' ; ATTACH ''x'' AS y; --' broke read_parquet([...])'s SQL literal exactly as the finding predicted, proving _register_comunicacoes interpolated arquivo_ia_url unvalidated."
---

# RunEvidence
