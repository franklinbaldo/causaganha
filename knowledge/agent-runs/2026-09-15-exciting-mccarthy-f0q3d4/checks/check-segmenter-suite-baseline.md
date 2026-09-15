---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-f0q3d4-check-segmenter-suite-baseline"
run_id: "2026-09-15-exciting-mccarthy-f0q3d4"
goal_id: "2026-09-15-exciting-mccarthy-f0q3d4-goal-scale-segmenter-reviews"
command: "uv run pytest tests/segmenter_dataset -q"
result: "passed"
evidence_id: null
summary: "365 testes, 0 falhas -- baseline antes de adjudicar os ReviewRecords desta rodada, confirmando que as 2 anotações extras já gravadas (doc_b8a4a405/doc_ec1f5133, não pareáveis) não quebraram nada."
---

# Check: suíte do segmenter_dataset, baseline pré-adjudicação

Confirma que as duas anotações extras gravadas antes da correção do filtro
de candidatos (evidence-red-nonindependent-pair) são mecanicamente válidas
e não introduziram nenhuma regressão na suíte.
