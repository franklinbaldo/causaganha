---
type: AgentEvidence
id: "2026-09-14-exciting-mccarthy-bueov4-evidence-pr-1484-merged"
run_id: "2026-09-14-exciting-mccarthy-bueov4"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1484"
summary: "PR #1484 ('fix(web): classify Internet Archive CORS-blocked datasets distinctly (#1482)') mesclado em main via squash merge (mcp__github__merge_pull_request), commit c65fd509f5f0cd745e87324ad7fb424ba34b6f0c. O primeiro merge (#1483) deixou o branch da PR 'behind' main; a política 'strict_required_status_checks_policy' do ruleset de main exigiu que o check obrigatório 'GitGuardian Security Checks' rodasse contra o head atualizado antes de permitir o merge (erro inicial: '405 Repository rule violations found -- Required status check GitGuardian Security Checks is expected', apesar do check já ter passado no head antigo). Resolvido com mcp__github__update_pull_request_branch (merge não destrutivo de main no branch da PR, sem rebase/force-push), aguardando a suíte completa de CI (CodeQL, web, tests (tjro), lint, compare-product-surfaces, GitGuardian, Analyze x4) terminar verde no novo head c6518915b13fad49521bec3a8d131741f459ea12 antes do merge final. Revisão independente confirmou SAFE TO MERGE previamente (evidence-review-pr-1484.md)."
---

# Evidência: PR #1484 mesclado

Squash merge de PR #1484 em `main`, commit `c65fd509f5f0cd745e87324ad7fb424ba34b6f0c`, após atualizar o branch com `main` (via update_pull_request_branch, não destrutivo) para satisfazer a política estrita de required-status-checks do ruleset (GitGuardian precisava rodar contra o novo head), e aguardar toda a suíte de CI ficar verde no head atualizado.
