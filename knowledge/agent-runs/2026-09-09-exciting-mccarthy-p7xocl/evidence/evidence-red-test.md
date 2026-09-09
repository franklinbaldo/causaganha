---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-p7xocl-evidence-red-test"
run_id: "2026-09-09-exciting-mccarthy-p7xocl"
goal_id: "2026-09-09-exciting-mccarthy-p7xocl-goal-catalog-scripts-csv-escaping"
kind: "test_red"
reference: "tests/test_append_manifest.py::test_get_new_uploads_preserves_comma_in_djen_raw"
summary: "Ran against unmodified scripts/append_manifest.py. Failed exactly as predicted: with djen_raw='network,timeout' quoted by DuckDB's CSV writer as '\"network,timeout\"', the naive str.split(',') shifts the row to 7 fields, and parts[5] (read as updated_at/downloaded_at) becomes 'timeout\"' instead of the real timestamp '2026-01-01T10:00:00Z'. AssertionError: assert 'timeout\"' == '2026-01-01T10:00:00Z'. This corrupts the downloaded_at field of manifest.jsonl, a public artifact appended and re-uploaded to Internet Archive (causaganha-catalog item) on every Update Catalog workflow run."
---

# Evidência: RED confirmado em get_new_uploads

O teste falhou exatamente como previsto contra o código não corrigido: `downloaded_at` corrompido para `'timeout"'` em vez do timestamp real, por causa do `str.split(',')` ingênuo sobre um campo `djen_raw` citado pelo escritor CSV do DuckDB.
