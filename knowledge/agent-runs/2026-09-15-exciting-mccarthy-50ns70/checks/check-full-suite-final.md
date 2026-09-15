---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-50ns70-check-full-suite-final"
run_id: "2026-09-15-exciting-mccarthy-50ns70"
goal_id: "2026-09-15-exciting-mccarthy-50ns70-goal-cors-probe-ci"
command: "uv run pytest -q"
result: "passed"
evidence_id: "2026-09-15-exciting-mccarthy-50ns70-evidence-generated-files-fixed"
summary: "check-full-suite-mid-round's 3 draft-cascade failures did NOT clear on their own once run.md was completed, unlike to0ars's precedent: `uv run okf-parser check` stayed conformant=true throughout (it does not flag extra undeclared fields), but scripts/check_agent_run_completeness.py's own stricter per-round validation caught two real authoring mistakes in this round's own AgentDecision/AgentEvidence records -- `decision-python-over-node-playwright.md` used a `decision:` key (schema field is `choice:`, with a required `question:`) and an `alternatives_considered` field the schema does not declare at all for AgentDecision; `evidence-live-probe-refresh.md` used `kind: \"runtime_behavior\"`, not a valid AgentEvidence.kind enum value (must be one of test_red/test_green/ci/diff/review/runtime/issue/pr/okf/other). Fixed both (renamed to choice/question, folded the alternatives-considered content into rationale prose; kind -> \"runtime\"), regenerated web/src/lib/processoConsultar.gen.ts and src/causaganha_mcp/_generated/domain_models.py (0-diff and 1-line diff respectively), then re-ran `uv run pytest -q`: full suite green, 0 failures. `uv run okf-parser check` stayed conformant=true (1335 concepts, 1338 markdown) throughout."
---

# Check: suíte completa final

As 3 falhas do rascunho não se resolveram sozinhas -- revelaram dois erros reais de autoria nesta rodada (campo `decision`/`alternatives_considered` inválido em `AgentDecision`, `kind` inválido em `AgentEvidence`). Corrigidos, arquivos gerados regenerados, suíte completa volta a ficar 100% verde.
