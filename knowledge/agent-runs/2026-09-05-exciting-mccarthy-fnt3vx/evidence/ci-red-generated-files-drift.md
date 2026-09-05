---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-fnt3vx-evidence-ci-red-generated-files-drift"
run_id: "2026-09-05-exciting-mccarthy-fnt3vx"
goal_id: "2026-09-05-exciting-mccarthy-fnt3vx-goal-purge-dead-experiment-imports"
kind: "ci"
reference: "PR #1162 CI on commit b6c5445 (superseding c9b2495): 'validate' (OKF knowledge workflow) failed at step 'Check generated domain models are up to date'; 'tests (tjro)' (CI workflow) failed at tests/web/test_generate_okf_zod_schemas.py::test_generated_zod_schemas_file_matches_current_knowledge_bundle"
summary: "Root cause confirmed by reproduction: this round's own knowledge/agent-runs/.../checks/no-references-grep.md is the first AgentCheck document in the whole bundle that omits evidence_id (a legitimately optional FK per okf.schema.sql's 'evidence_id VARCHAR REFERENCES ...' with no NOT NULL -- this check has no distinct evidence file, it is a plain grep). okf-parser's schema/zod generators infer field optionality from the actual data across the bundle, so adding the first AgentCheck instance without evidence_id correctly makes the generated AgentCheck.evidence_id optional -- but src/causaganha_mcp/_generated/domain_models.py and web/src/lib/processoConsultar.gen.ts were committed before this instance existed and had it as required. Verified via a clean git worktree of origin/main (c9d6eca): regenerating both files there produces zero diff, proving the drift did not exist on main and was introduced by this PR's own new content, not a pre-existing base-branch failure. Fix: ran scripts/generate_okf_domain_models.py and scripts/generate_okf_zod_schemas.py and committed the two resulting one-line diffs (both files now mark evidence_id optional, matching the schema)."
---

# Evidência — CI vermelho causado pela própria rodada, corrigido

A rodada introduziu o primeiro `AgentCheck` sem `evidence_id` (campo legitimamente opcional no schema), o que corretamente tornou o campo opcional nos artefatos gerados — mas os dois arquivos gerados versionados ainda assumiam obrigatoriedade. Reproduzido localmente contra um worktree limpo do `main` (sem diff), confirmando que a causa é desta PR, não do branch base. Corrigido regenerando os dois artefatos.
