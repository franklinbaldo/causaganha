---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-i23hxr-evidence-red-test-4-findings"
run_id: "2026-09-24-exciting-mccarthy-i23hxr"
kind: "test_red"
reference: "tests/segmenter_dataset/test_segmenter_audit_scripts.py::test_real_store_has_no_long_anchor_or_dispositivo_inside_voto_findings"
summary: "Novo teste de regressao, escrito antes do reparo, afirma que find_anti_patterns() nao reporta nenhum finding do tipo long_anchor/dispositivo_inside_voto contra o store real. Rodado antes do reparo: FAILED com exatamente os 4 achados esperados -- doc_b0c364907d4409d67d4d2a734c7bd54d/doc_b8a4a405e45ffe9a1ab11cf902f849e2/doc_c502b14fd24cd8133897a1863d25e30a com long_anchor, doc_c772414481d672a6886be6f4f9d261c2 com dispositivo_inside_voto. `AssertionError: assert {'doc_b0c364...': ['long_anchor'], ...} == {}`."
---

# Evidencia: teste RED antes do reparo

```
$ uv run pytest -q tests/segmenter_dataset/test_segmenter_audit_scripts.py::test_real_store_has_no_long_anchor_or_dispositivo_inside_voto_findings
...
AssertionError: assert {'doc_b0c3649...inside_voto']} == {}
  Left contains 4 more items:
  {'doc_b0c364907d4409d67d4d2a734c7bd54d': ['long_anchor'],
   'doc_b8a4a405e45ffe9a1ab11cf902f849e2': ['long_anchor'],
   'doc_c502b14fd24cd8133897a1863d25e30a': ['long_anchor'],
   'doc_c772414481d672a6886be6f4f9d261c2': ['dispositivo_inside_voto']}
FAILED
```

Confirma que os 4 achados eram reais e ja presentes no store antes de
qualquer mudanca desta rodada -- nao um artefato do novo teste.
