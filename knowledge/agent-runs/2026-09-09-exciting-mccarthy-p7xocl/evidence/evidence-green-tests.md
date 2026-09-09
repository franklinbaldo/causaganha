---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-p7xocl-evidence-green-tests"
run_id: "2026-09-09-exciting-mccarthy-p7xocl"
goal_id: "2026-09-09-exciting-mccarthy-p7xocl-goal-catalog-scripts-csv-escaping"
kind: "test_green"
reference: "tests/test_append_manifest.py::test_get_new_uploads_preserves_comma_in_djen_raw"
summary: "After switching get_new_uploads() in scripts/append_manifest.py from str.split(',') to csv.reader(io.StringIO(text)), the same test that failed pre-fix now passes: downloaded_at correctly reads '2026-01-01T10:00:00Z' even with a comma-quoted djen_raw field ahead of it. tests/test_catalog_parsing.py (18 tests, unrelated functions in scripts/generate_catalog.py) and tests/test_update_catalog_workflow.py stayed green unchanged, confirming no regression to sibling parsing code that was deliberately left untouched (see decision-scope-limited-to-append-manifest)."
---

# Evidência: GREEN pós-fix

`get_new_uploads()` agora usa `csv.reader` e o teste que provava a corrupção passa. Suítes irmãs permanecem verdes, sem regressão.
