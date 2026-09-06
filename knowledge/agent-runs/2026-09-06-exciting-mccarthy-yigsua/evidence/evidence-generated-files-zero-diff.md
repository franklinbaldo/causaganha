---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-yigsua-evidence-generated-files-zero-diff"
run_id: "2026-09-06-exciting-mccarthy-yigsua"
kind: "runtime"
reference: "uv run --no-sync python scripts/generate_okf_domain_models.py && uv run --no-sync python scripts/generate_okf_zod_schemas.py; git status --short (twice: once with the invented field names, once after conforming to knowledge/.okf/specs/agent*.schema.sql)"
summary: "First run (invented field names title/motivation/decision/reason/procedure): git status showed src/causaganha_mcp/_generated/domain_models.py and web/src/lib/processoConsultar.gen.ts as modified, a 20-line diff each flipping several AgentCheck/AgentDecision/AgentGoal fields from required to optional and adding new optional fields never used by any prior round. Second run, after rewriting this round's goal/decision/check records to use the schema-declared field names (goal/rationale/success_signal/status; question/choice/rationale/goal_id; command/result/evidence_id/summary/goal_id): git status showed no changes to either generated file — byte-for-byte match with what is already committed, and `uv run pytest -q` no longer fails test_generated_domain_models_file_matches_current_knowledge_bundle nor test_generated_zod_schemas_file_matches_current_knowledge_bundle."
---

# Evidência — diff zero nos arquivos gerados após conformar nomes de campo

Regenerar `domain_models.py`/`processoConsultar.gen.ts` com os nomes de campo corretos produz diff zero contra o que já está commitado — confirma que a causa da falha era puramente os nomes de campo inventados nesta rodada, não uma mudança real de versão do `okf-parser` (testado com 0.45.6 e 0.45.8, ambos com o mesmo resultado antes/depois da correção).
