---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-yz281l-evidence-green-test"
run_id: "2026-09-15-exciting-mccarthy-yz281l"
goal_id: "2026-09-15-exciting-mccarthy-yz281l-goal-row-group-size-a1b"
kind: "test_green"
reference: "tests/test_exporter.py (13 tests, incluindo os 2 de TestRowGroupSize)"
summary: "Apos reverter as mudancas temporarias em exporter.py, `uv run pytest tests/test_exporter.py -q` -- 13 passed. Inclui os dois novos testes de TestRowGroupSize (contagem de row groups + presenca literal de ROW_GROUP_SIZE 122880 na SQL), alem das 11 suites pre-existentes (TestTableOrderKeys, TestCnjNormalization, TestCnjLayoutCertification), todas intactas -- nenhuma regressao introduzida pela mudanca (ROW_GROUP_SIZE 122880 pinado explicitamente + comentario inline em exporter.py + 2 novos testes)."
---

# Evidência: GREEN da suíte de exporter.py

`uv run pytest tests/test_exporter.py -q` → `12 passed`. Confirma que o novo teste de contrato (ROW_GROUP_SIZE) e o comentário adicionado a `exporter.py` não quebram nenhum dos testes pré-existentes de ordenação, normalização CNJ e certificação de layout.
