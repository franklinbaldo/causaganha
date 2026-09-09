---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-pf1xhn-evidence-pr-1356-merged"
run_id: "2026-09-09-exciting-mccarthy-pf1xhn"
goal_id: "2026-09-09-exciting-mccarthy-pf1xhn-goal-juris-datajud-ia-fallback"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1356"
summary: "PR #1356 driven to green after one CI-fix cycle: initial push (5250970) failed the 'web' check (renderedContracts.integration.test.ts timing out at 120s due to a real IA network fallback slipping into the test fixture harness); pushed a fix (dec2804) isolating reconcile_processos.ensure_juris_parquets()/ensure_datajud_parquets() from real network in scripts/render_contract_fixture.py. All 10 check runs on dec2804 (CodeQL, web, lint, tests (tjro), validate, 4x CodeQL Analyze, GitGuardian) completed with conclusion=success, mergeable_state 'clean', zero pending reviews/comments. Squash-merged via mcp__github__merge_pull_request as commit 574e5f79c5e33a1bfb7ace1ba3d52041d6916bcc onto main."
---

# Evidência: PR #1356 mesclada

PR levada a verde após um ciclo de correção de CI (timeout de rede real isolado do harness de fixtures). Todos os 10 checks passaram na SHA final, sem revisões pendentes. Mesclada via squash como `574e5f7`.
