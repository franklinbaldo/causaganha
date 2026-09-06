---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-fpldz1-evidence-okf-generator-drift-caught"
run_id: "2026-09-06-exciting-mccarthy-fpldz1"
goal_id: "2026-09-06-exciting-mccarthy-fpldz1-goal-continue-with-agent"
kind: "okf"
reference: "uv run pytest -q (tests/causaganha_mcp/test_okf_domain_models.py, tests/web/test_generate_okf_zod_schemas.py) before and after `uv run python scripts/generate_okf_zod_schemas.py` / `generate_okf_domain_models.py`"
summary: "Full pytest run after writing this round's own AgentEvidence files failed both generated-bindings drift tests. Regenerating web/src/lib/processoConsultar.gen.ts showed the exact cause: knowledge/agent-runs/2026-09-06-exciting-mccarthy-fpldz1/evidence/evidence-runtime-browser-verification.md was first written without a `reference` field, and okf.schema.sql declares AgentEvidence.reference NOT NULL — the exporter's derived Zod schema silently widened `reference` from required to `.optional()` to accommodate the gap, which would have shipped a real weakening of the AgentEvidence contract for every future AgentEvidence document, not just this one. Fixed by adding the missing `reference` field to that evidence file (matching every other AgentEvidence document's shape) instead of accepting the drifted, widened schema. Regenerating both bindings afterward produced a zero-diff, and the two previously-failing tests passed."
---

# Evidência OKF — drift de schema pego durante a própria rodada

Um `AgentEvidence` desta própria rodada, escrito sem `reference`, teria afrouxado silenciosamente o contrato gerado (`reference` viraria opcional para todo `AgentEvidence` futuro). Corrigido preenchendo o campo em vez de aceitar o schema gerado já alargado — reforça, na prática, que os testes de regeneração (`test_okf_domain_models.py`/`test_generate_okf_zod_schemas.py`) fazem exatamente o trabalho de proteção que deveriam.
