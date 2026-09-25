---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-i23hxr-evidence-repair-script-and-green"
run_id: "2026-09-24-exciting-mccarthy-i23hxr"
kind: "test_green"
reference: "scripts/repair_segmenter_semantic_audit_2026_09_batch2.py; tests/segmenter_dataset/test_segmenter_audit_scripts.py::test_real_store_has_no_long_anchor_or_dispositivo_inside_voto_findings"
summary: "scripts/repair_segmenter_semantic_audit_2026_09_batch2.py escreveu 4 AnnotationRecord supersedentes (validate_record aprovou cada uma antes da escrita -- offsets, pares, ontologia, duplicatas de ancora unica): 3x acordao_decisorio_inicio truncado de um paragrafo formulaico inteiro (127-202 chars) para a mesma frase curta 'Vistos, relatados e discutidos estes autos' (44 chars, sob o limite de ~120 da Regra 1 do guideline, mesma familia do proprio exemplo do guideline para essa categoria); 1x doc_c772414481d672a6886be6f4f9d261c2 com dispositivo_abertura+resultado removidos de dentro do voto individual e um unico resultado novo adicionado sobre 'NAO CONHECIDO' dentro do acordao_decisorio colegiado (mesmo padrao ja usado pelo documento irmao doc_b0c364907d4409d67d4d2a734c7bd54d). Apos o reparo: uv run python scripts/segmenter_semantic_audit.py so reporta os 7 findings collapsed ja conhecidos e alocados (zero long_anchor, zero dispositivo_inside_voto). O teste RED (evidence-red-test-4-findings) passou a GREEN."
---

# Evidencia: reparo e teste GREEN

```
$ uv run python scripts/repair_segmenter_semantic_audit_2026_09_batch2.py
Wrote 4 superseding annotations:
  ann_fbbe79a1785dd087a70aebfa13ec6ef4
  ann_a5b0d97027504f997708778927f77625
  ann_308d9533f73be5bc5d92791882300faa
  ann_a747b914d7e67395efc3f56c5230b6c1

$ uv run python scripts/segmenter_semantic_audit.py
# 7 documentos, todos com finding type == "*_collapsed" (a allowlist
# ja conhecida e testada por test_real_store_has_at_most_the_one_known_collapsed_false_positive).
# Nenhum long_anchor, nenhum dispositivo_inside_voto.

$ uv run pytest -q tests/segmenter_dataset/test_segmenter_audit_scripts.py
......                                                                   [100%]
```

Registros originais (flawed) preservados em disco para historico de
auditoria -- nenhuma edicao in-place, per RFC 0012 Sec3.1
(imutabilidade de registro).
