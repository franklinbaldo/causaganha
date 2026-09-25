---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-230b86-evidence-red-discover-catalog-items"
run_id: "2026-09-25-exciting-mccarthy-230b86"
goal_id: "2026-09-25-exciting-mccarthy-230b86-goal-catalog-discovery-allowlist"
kind: "test_red"
reference: "tests/test_archive_partitions.py::test_verified_catalog_discovery_uses_project_manifest_allowlist, tests/test_archive_partitions.py::test_verified_catalog_discovery_refuses_global_search_when_manifest_empty"
summary: "uv run pytest tests/test_archive_partitions.py -k verified_catalog_discovery -q -- ambos os testes falharam com AttributeError: module 'scripts.generate_catalog' has no attribute 'discover_catalog_items', confirmando RED antes de qualquer mudanca de producao."
---

# Evidência: RED

Dois testes escritos primeiro contra a API alvo
(`catalog.discover_catalog_items`, ainda inexistente). Ambos falharam com
`AttributeError`, confirmando que o comportamento desejado (uma rebuild
`--verified-inventory` nunca cai em `list_ia_items()`) ainda não existe.
