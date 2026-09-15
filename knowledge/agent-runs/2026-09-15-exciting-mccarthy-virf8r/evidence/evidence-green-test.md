---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-virf8r-evidence-green-test"
run_id: "2026-09-15-exciting-mccarthy-virf8r"
goal_id: "2026-09-15-exciting-mccarthy-virf8r-goal-scale-segmenter-reviews"
kind: "test_green"
reference: "tests/segmenter_dataset/test_adjudicate_segmenter_review.py (6/6 passed)"
summary: "Após adicionar --allowed-unmatched a scripts/adjudicate_segmenter_review.py::main (mirroring o mesmo parâmetro já existente em scripts/annotate_second_independent.py), os 6 testes do arquivo passam, incluindo o novo test_main_passes_allowed_unmatched_through_cli que confirma o valor declarado chega intacto ao ReviewRecord.allowed_unmatched persistido."
---

# GREEN: --allowed-unmatched exposto na CLI

`uv run pytest tests/segmenter_dataset/test_adjudicate_segmenter_review.py -q` -- 6 passed. A correção desbloqueou a adjudicação real do doc_0bb1cdf4d3ce8cb2400765e788c767e4 (rev_4fc943148e7fdffe8898016d2e245beb), cujo ementa genuinamente não tem cue de fechamento neste modelo de acórdão por tópicos.
