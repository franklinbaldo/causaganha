---
type: "RunEvidence"
id: "run-evidence/20260914t122515z-do-the-best-useful-work-availab/evidence-red-green-cnj-writer"
run: "runs/20260914T122515Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_exporter.py, tests/test_consolidate_export_unification.py (branch fix/parquet-cnj-writer-unification)"
summary: "RED: 5 novos testes falharam contra o código atual (normalização CNJ ausente, ordenação antiga, sem footer de certificação, _export_table_sync legado não normaliza/certifica). GREEN após implementar: CNJ_LAYOUT_TABLES + normalização em exporter.py, _TABLE_ORDER_KEYS CNJ-first para comunicacoes/processos, kv_metadata_for_export(table_name=) certificando causaganha.layout/causaganha.cnj_normalization, CURRENT_LAYOUT_REVISION 1->2, e _export_table_sync em scripts/pipeline/consolidate.py delegando para causaganha.consolidate.exporter.export_table_sync. 'uv run pytest -q tests/test_exporter.py tests/test_consolidate_export_unification.py' -> 12 passed. Suites relacionadas (schema_registry, consolidation, consolidate/, candidates, consolidation_manifest) -> all green, sem regressão."
goal: "run-goals/20260914t122515z-do-the-best-useful-work-availab/goal-unify-cnj-writer"
---

# RunEvidence
