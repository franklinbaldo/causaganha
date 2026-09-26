---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-p08457-check-mechanical-verification"
run_id: "2026-09-26-exciting-mccarthy-p08457"
goal_id: "2026-09-26-exciting-mccarthy-p08457-goal-1051-test-split-adjudication"
command: "script ad-hoc: xml.etree.ElementTree.fromstring + segmenter_dataset.store._text_element_to_labels + segmenter_dataset.mechanical.validate_record, para cada segunda anotacao e cada resolucao de adjudicacao, antes de qualquer escrita no store"
result: "observed"
evidence_id: "2026-09-26-exciting-mccarthy-p08457-evidence-mechanical-verification"
summary: "TRF6: segunda anotacao original tinha overlap (ref_processual aninhado em cabecalho_inicio) -- corrigido, revalidado limpo (0 problems). TRF2: segunda anotacao limpa de primeira (0 problems, com allowed_unmatched=ementa). Ambas as resolucoes de adjudicacao verificadas limpas (verbatim match True, 0 problems) antes de rodar scripts/adjudicate_segmenter_review.py."
---

# Check: verificacao mecanica pre-ingestao
