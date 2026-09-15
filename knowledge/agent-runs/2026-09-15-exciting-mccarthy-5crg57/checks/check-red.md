---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-5crg57-check-red"
run_id: "2026-09-15-exciting-mccarthy-5crg57"
goal_id: "2026-09-15-exciting-mccarthy-5crg57-goal-first-real-review-record"
command: "uv run pytest tests/segmenter_dataset/test_annotate_second_independent.py tests/segmenter_dataset/test_adjudicate_segmenter_review.py -q"
result: "failed"
evidence_id: "2026-09-15-exciting-mccarthy-5crg57-evidence-red-test"
summary: "Falha de coleta esperada (RED): os dois scripts ainda não existiam. Confirma que os testes exercitam código real, não um stub já presente."
---

# Check: RED antes da implementação

Rodado imediatamente após escrever os dois arquivos de teste, antes de criar `scripts/annotate_second_independent.py`/`scripts/adjudicate_segmenter_review.py`.
