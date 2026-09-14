---
type: AgentEvidence
id: "2026-09-14-exciting-mccarthy-to0ars-evidence-generated-files-regenerated"
run_id: "2026-09-14-exciting-mccarthy-to0ars"
goal_id: "2026-09-14-exciting-mccarthy-to0ars-goal-verify-values-bucket"
kind: "diff"
reference: "web/src/lib/processoConsultar.gen.ts (+2/-2), src/causaganha_mcp/_generated/domain_models.py (+2/-2)"
summary: "After completing this round's report, `uv run pytest -q` still showed 2 failures (not the usual 3-test draft cascade the scaffold warns about, since completed_at/primary_goal_id/result_summary/next_move were already filled in): tests/web/test_generate_okf_zod_schemas.py and tests/causaganha_mcp/test_okf_domain_models.py, both drift gates comparing a checked-in generated file against what scripts/generate_okf_zod_schemas.py / generate_okf_domain_models.py produce from the current knowledge/ bundle right now. Root cause: this round's own check-full-suite-mid-round.md (AgentCheck) and decision-agentrun-vs-wisk-policy-conflict.md (AgentDecision) are the first instances in the whole bundle to write `evidence_id: null` / `goal_id: null` explicitly (every prior round always either supplied a real id or omitted the optional key -- never wrote a literal null), so the generators correctly inferred these two fields as nullable for the first time. This is a genuine, permanent shape change from real new data, not the scaffold's documented transient-draft artifact (which resolves itself without regenerating anything) -- so, per CLAUDE.md's own rule ('Canonical source is the manifest... Don't generate cache JSONs from random sources', the general principle that generated files are mechanically derived and must be regenerated, never hand-patched, when their real source changes), ran both generators and committed their output. `uv run pytest -q`: 100% green repo-wide afterward (0 failures). `uv run ruff check .` / `ruff format --check .`: clean."
---

# Evidência: arquivos gerados (Zod/domain models) regenerados

Dois testes de drift falharam ao final da rodada, não pelo cascade documentado de rascunho, mas porque este é o primeiro `AgentCheck`/`AgentDecision` do bundle inteiro a escrever `null` explícito em `evidence_id`/`goal_id` (rodadas anteriores sempre preenchiam um id real ou omitiam a chave). Mudança real e permanente de forma, não artefato transitório -- rodados os dois geradores (`generate_okf_zod_schemas.py`, `generate_okf_domain_models.py`), suíte completa volta a 100% verde.
