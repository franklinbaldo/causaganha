---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-6kxfkh-check-segmenter-suite"
run_id: "2026-09-15-exciting-mccarthy-6kxfkh"
command: "uv run pytest tests/segmenter_dataset -q"
result: "passed"
evidence_id: "2026-09-15-exciting-mccarthy-6kxfkh-evidence-audit-allowlist-fix"
summary: "377 testes, 0 falhas, apos a correcao de allowlist em test_segmenter_audit_scripts.py."
---

# Check: suite completa de segmenter_dataset

377 testes, 0 falhas, apos a correcao de allowlist em
`test_segmenter_audit_scripts.py::test_real_store_has_at_most_the_one_known_collapsed_false_positive`
(ver evidence-audit-allowlist-fix para o RED original e a causa raiz).
