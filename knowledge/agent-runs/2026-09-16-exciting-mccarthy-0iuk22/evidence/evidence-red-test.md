---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-0iuk22-evidence-red-test"
run_id: "2026-09-16-exciting-mccarthy-0iuk22"
goal_id: "2026-09-16-exciting-mccarthy-0iuk22-goal-djen-sample-corpus-growth"
kind: "test_red"
reference: "tests/segmenter_dataset/test_ingest_djen_sample_technique1_batch.py"
summary: "First run of the new test suite against the new script (before fixing the test fixtures) failed 2/6 tests with pydantic_core.ValidationError: 'label offsets must satisfy 0 <= start < end, got start=39 end=39' -- the acordao fixture used a malformed pair tag (<relatorio_fim></relatorio_fim>, zero-width) that does not match the guideline's actual wrapper-element pair syntax (<relatorio><inicio>...</inicio>...<fim>...</fim></relatorio>). Fixed by rewriting the fixtures to use only single-anchor flat categories (dispositivo_abertura, resultado), which sidesteps the pair-wrapper syntax entirely and is sufficient to test this script's own new behavior (tribunal/document_type derivation, unsupported-type skip, verbatim-fidelity skip)."
---

# Evidencia: RED antes de corrigir os fixtures de teste

```
FAILED tests/segmenter_dataset/test_ingest_djen_sample_technique1_batch.py::test_ingest_maps_sentenca_document_type_and_writes_document
FAILED tests/segmenter_dataset/test_ingest_djen_sample_technique1_batch.py::test_ingest_maps_acordao_document_type
...
E   pydantic_core._pydantic_core.ValidationError: 1 validation error for Label
E     Value error, label offsets must satisfy 0 <= start < end, got start=39 end=39
```

O erro estava no proprio teste (fixture de anotacao marcada mal-formada),
nao no script novo -- mas e um RED genuino produzido antes de qualquer
ajuste, evidenciando que os testes de fato exercitam o parsing real de tags
Technique 1 (`_text_element_to_labels`) e nao apenas simulam um caminho
feliz.
