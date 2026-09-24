---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-e3tk18-check-pytest-segmenter-dataset"
run_id: "2026-09-24-exciting-mccarthy-e3tk18"
goal_id: "2026-09-24-exciting-mccarthy-e3tk18-goal-fix-dead-ref-normativa-overlap-detector"
command: "uv run pytest -q tests/segmenter_dataset"
result: "passed"
evidence_id: "2026-09-24-exciting-mccarthy-e3tk18-evidence-green-fix-and-real-corpus-clean"
summary: "262 testes, 100% verde apos a correcao e os 5 novos testes (4 sinteticos + 1 guarda de regressao contra o corpus real)."
---

# Check: suite completa de segmenter_dataset

Confirma que a correcao do detector e os novos testes nao quebram
nenhum teste existente do pacote.
