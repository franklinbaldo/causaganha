---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-5txmmk-check-reconcile-suite"
run_id: "2026-09-25-exciting-mccarthy-5txmmk"
goal_id: "2026-09-25-exciting-mccarthy-5txmmk-goal-reconcile-identity-check"
command: "uv run pytest -q tests/test_reconcile_processos.py"
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-5txmmk-evidence-green-identity-check"
summary: "35/35 testes verdes -- os 4 novos de TestArtifactIdentityVerification mais todos os 31 pre-existentes (discovery allowlist, fluxo feliz JURIS/DataJud/STJ/DJEN, corrupted parquet, source coverage report, local-file provenance warning), sem nenhuma regressao apos a mudanca de producao e o ajuste de fixtures."
---

# Check: suite completa de tests/test_reconcile_processos.py
