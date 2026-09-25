---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-i23hxr-check-governance-status"
run_id: "2026-09-24-exciting-mccarthy-i23hxr"
command: "uv run python scripts/segmenter_governance_status.py"
result: "observed"
evidence_id: "2026-09-24-exciting-mccarthy-i23hxr-evidence-repair-script-and-green"
summary: "document_count=193 (inalterado -- o reparo desta rodada nao adiciona documentos), annotation_count=250 (246+4 supersedentes do reparo), review_count=31, val_ceiling=test_ceiling=29 (inalterado, ainda abaixo do piso RFC 0012 Sec5 item4 de >=30/>=30). Confirma que o reparo desta rodada nao teve efeito colateral sobre document_count nem sobre os ceilings de split -- exatamente o esperado, ja que cada reparo e uma AnnotationRecord supersedente sobre um documento ja existente, nao um novo documento."
---

# Check: governance status pos-reparo

Rodado apos o reparo para confirmar que document_count/ceilings nao
mudaram de forma inesperada -- o objetivo desta rodada era corrigir
qualidade de anotacoes ja existentes, nao crescer o corpus.
