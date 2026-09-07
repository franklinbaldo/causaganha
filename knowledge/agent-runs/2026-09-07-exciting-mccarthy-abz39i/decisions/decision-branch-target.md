---
type: AgentDecision
id: "2026-09-07-exciting-mccarthy-abz39i-decision-branch-target"
run_id: "2026-09-07-exciting-mccarthy-abz39i"
goal_id: "2026-09-07-exciting-mccarthy-abz39i-goal-fix-pr-1247-http-health"
question: "PR #1247 lives on branch feat/http-public-mcp-profile, owned by the repo owner. Should this session push the one-line fix directly onto that branch, or deliver it through this session's own designated branch as a PR targeting feat/http-public-mcp-profile?"
choice: "Deliver via this session's own branch (claude/exciting-mccarthy-abz39i), based on feat/http-public-mcp-profile's tip, opened as a PR with base=feat/http-public-mcp-profile rather than main."
rationale: "This session's git instructions are explicit: develop on claude/exciting-mccarthy-abz39i and never push to a different branch without explicit permission. feat/http-public-mcp-profile is a different branch belonging to the repo owner's own PR, and no explicit permission to push onto it was given — only a general instruction to advance in-progress PRs. A PR-onto-PR targeting the feature branch (rather than main) respects both constraints: it keeps this session's commits on its own branch while still landing the fix exactly where #1247 needs it, and once #1247 merges to main this fix's history rides along with it. The alternative (pushing straight to feat/http-public-mcp-profile) would have been faster by one review hop but violates the explicit branch rule for a fix that isn't urgent enough to need it."
---

# Decisão: onde entregar a correção

Em vez de empurrar direto para `feat/http-public-mcp-profile` (branch de outra PR, do dono do repositório), a correção foi entregue via `claude/exciting-mccarthy-abz39i` (branch designada desta sessão) como uma PR com base na própria `feat/http-public-mcp-profile`, respeitando a regra de nunca empurrar para uma branch diferente sem permissão explícita.
