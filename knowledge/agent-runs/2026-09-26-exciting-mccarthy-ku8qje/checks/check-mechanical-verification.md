---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-ku8qje-check-mechanical-verification"
run_id: "2026-09-26-exciting-mccarthy-ku8qje"
goal_id: "2026-09-26-exciting-mccarthy-ku8qje-goal-segmenter-batch28"
command: "segmenter_dataset.store._text_element_to_labels + segmenter_dataset.mechanical.validate_record sobre os dois rascunhos anotados, ANTES de qualquer ingestão real (script ad-hoc em /tmp/verify_batch28.py e /tmp/verify_batch28b.py)"
result: "passed"
evidence_id: "2026-09-26-exciting-mccarthy-ku8qje-evidence-batch28-ingested"
summary: "TJPB/578828501: reconstrução verbatim == texto-fonte (True); mechanical_problems=[] após override `relatorio`. TJMT/74433596: reconstrução verbatim == texto-fonte (True); mechanical_problems=[] após overrides `relatorio`+`custas`+`honorarios`. Nenhum dos dois precisou de correção de texto/tag -- ambos passaram na primeira tentativa de cada subagente."
---

# Check: verificação mecânica pré-ingestão dos dois rascunhos do Lote 28
