---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-wvzu11-evidence-red-test"
run_id: "2026-09-15-exciting-mccarthy-wvzu11"
kind: "test_red"
reference: "tests/segmenter_dataset/test_segmenter_governance_status.py"
summary: "Antes de scripts/segmenter_governance_status.py existir, `uv run pytest tests/segmenter_dataset/test_segmenter_governance_status.py -q` falhou com FileNotFoundError nos 4 testes (o helper load_script tenta importar o script que ainda não existe), confirmando RED genuíno antes da implementação."
---

# Evidência: RED

```
FAILED tests/segmenter_dataset/test_segmenter_governance_status.py::test_reports_zero_evaluation_eligible_when_store_has_no_reviews
FAILED tests/segmenter_dataset/test_segmenter_governance_status.py::test_evaluation_eligible_count_reflects_accepted_reviews
FAILED tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_has_zero_evaluation_eligible_documents
FAILED tests/segmenter_dataset/test_segmenter_governance_status.py::test_main_prints_json_status
FileNotFoundError: [Errno 2] No such file or directory: '.../scripts/segmenter_governance_status.py'
```
