---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-5crg57-check-assign-splits-cli"
run_id: "2026-09-15-exciting-mccarthy-5crg57"
goal_id: "2026-09-15-exciting-mccarthy-5crg57-goal-first-real-review-record"
command: "uv run python -m segmenter_dataset assign-splits --data-root data/segmenter/ --seed 771 (rodado com 1 e depois com 2 documentos evaluation-eligible)"
result: "observed"
evidence_id: "2026-09-15-exciting-mccarthy-5crg57-evidence-second-real-review"
summary: "Com 1 e com 2 documentos eval-eligible, o CLI completo de assign-splits recusa produzir um manifest (val ou test vazio) -- limitação pré-existente do splitter (RFC 0012 §10, achado de review do PR #838: sem fallback para grupo menor), não uma regressão desta rodada. O sinal de sucesso do goal (evaluation_eligible_count>=1 via segmenter_governance_status.py) já estava satisfeito antes desta checagem adicional."
---

# Check: limite honesto do CLI de assign-splits com poucos documentos eval-eligible

Rodado como verificação extra, além do sinal de sucesso já declarado no goal, para checar se o mecanismo end-to-end (não só o diagnóstico agregado) já produz um split real. Resultado: ainda não, com apenas 2 documentos -- decisão registrada (decision-scope-boundary-assign-splits-fix) de não perseguir uma correção do algoritmo do splitter nesta mesma rodada.
