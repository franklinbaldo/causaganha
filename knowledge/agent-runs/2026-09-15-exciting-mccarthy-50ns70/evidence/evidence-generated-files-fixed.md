---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-50ns70-evidence-generated-files-fixed"
run_id: "2026-09-15-exciting-mccarthy-50ns70"
goal_id: "2026-09-15-exciting-mccarthy-50ns70-goal-cors-probe-ci"
kind: "diff"
reference: "web/src/lib/processoConsultar.gen.ts, src/causaganha_mcp/_generated/domain_models.py"
summary: "After fixing this round's own AgentDecision (choice/question instead of decision/alternatives_considered) and AgentEvidence (kind: runtime instead of runtime_behavior) authoring mistakes, ran `uv run python scripts/generate_okf_zod_schemas.py` and `uv run python scripts/generate_okf_domain_models.py`. Zod schema output: 0 diff (already matched, since choice/question fixes were the only shape-relevant change and description/goal_id/etc. were unaffected). Python domain models: 1 line changed (choice: str became non-optional now that every AgentDecision instance in the bundle supplies it consistently, alternatives_considered's Field(default=None) line removed). Both files committed alongside the schema-authoring fix."
---

# Evidência: arquivos gerados corrigidos

`processoConsultar.gen.ts` (0 diff) e `domain_models.py` (1 linha) regenerados após corrigir os campos de `AgentDecision`/`AgentEvidence` desta própria rodada.
