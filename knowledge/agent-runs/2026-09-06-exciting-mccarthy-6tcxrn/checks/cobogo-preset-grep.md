---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-6tcxrn-check-cobogo-preset-grep"
run_id: "2026-09-06-exciting-mccarthy-6tcxrn"
goal_id: "2026-09-06-exciting-mccarthy-6tcxrn-goal-1178-single-theme-decision"
command: "cd web && npm ci && grep -in 'theme|tema|light|dark|condition|semanticTokens' node_modules/cobogo/preset/index.mjs"
result: "observed"
evidence_id: "2026-09-06-exciting-mccarthy-6tcxrn-evidence-cobogo-preset-no-dark-mode"
summary: "Confirms live-installed Cobogó preset defines no dark-mode mechanism, grounding the single-theme decision instead of assuming it from the issue text alone."
---

# Check — preset Cobogó investigado ao vivo (não assumido)
