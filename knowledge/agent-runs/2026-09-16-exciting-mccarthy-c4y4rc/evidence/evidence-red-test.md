---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-c4y4rc-evidence-red-test"
run_id: "2026-09-16-exciting-mccarthy-c4y4rc"
kind: "test_red"
reference: "tests/segmenter_dataset/test_segmenter_governance_status.py"
summary: "3 testes falharam antes da mudanca de scripts/segmenter_governance_status.py: test_reports_zero_evaluation_eligible_when_store_has_no_reviews e test_real_store_has_at_least_one_evaluation_eligible_document falharam com KeyError: 'corpus_scale_blocks_floor' (novos campos ainda inexistentes); test_val_test_ceiling_reflects_full_adjudication_of_current_corpus (novo) e o teste central do achado desta rodada."
---

# Evidencia: RED antes de estender segmenter_governance_status.py

```
FAILED tests/segmenter_dataset/test_segmenter_governance_status.py::test_reports_zero_evaluation_eligible_when_store_has_no_reviews
FAILED tests/segmenter_dataset/test_segmenter_governance_status.py::test_val_test_ceiling_reflects_full_adjudication_of_current_corpus
FAILED tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_has_at_least_one_evaluation_eligible_document
...
E       KeyError: 'corpus_scale_blocks_floor'
```

Os 3 testes cobrem: (1) um store vazio recem-criado ainda reporta os novos
campos corretamente (val_count=0, meets_rfc_0012_split_floor=False,
corpus_scale_blocks_floor=True); (2) um corpus sintetico de 4 documentos,
100% adjudicado, prova que `val_count`/`test_count` batem exatamente com
`val_ceiling_at_full_adjudication`/`test_ceiling_at_full_adjudication`
quando a adjudicacao ja esta completa, e que ambos ficam abaixo de 30; (3)
o guard de regressao contra o store real (`data/segmenter`) e atualizado
para exigir `corpus_scale_blocks_floor is True` hoje.
