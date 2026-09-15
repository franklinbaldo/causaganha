---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-wvzu11-evidence-green-test"
run_id: "2026-09-15-exciting-mccarthy-wvzu11"
kind: "test_green"
reference: "tests/segmenter_dataset/test_segmenter_governance_status.py, scripts/segmenter_governance_status.py"
summary: "Após implementar scripts/segmenter_governance_status.py (compute_governance_status + main), os 4 testes ficaram GREEN: 2 testes de fixture sintética (sem reviews -> blocked_on_reviews=True; com 1 review aceito de anotações independentes -> blocked_on_reviews=False), 1 teste de regressão contra a store real (data/segmenter: blocked_on_reviews=True, review_count=0), e 1 teste do CLI main() imprimindo JSON + WARNING."
---

# Evidência: GREEN

```
uv run pytest tests/segmenter_dataset/test_segmenter_governance_status.py -q
....                                                                     [100%]
```

`uv run ruff check` e `uv run ruff format --check` limpos nos dois arquivos novos.
