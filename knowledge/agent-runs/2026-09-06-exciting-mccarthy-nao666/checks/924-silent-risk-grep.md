---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-nao666-check-924-silent-risk-grep"
run_id: "2026-09-06-exciting-mccarthy-nao666"
goal_id: "2026-09-06-exciting-mccarthy-nao666-goal-close-924-live-verification"
command: "grep -n 'isDatasetStale\\|datasetStale' web/src/components/ProcessoLookup.svelte"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-nao666-evidence-924-silent-risk-staleness-ui"
summary: "Confirms the staleness warning suggested in #924's 'risco silencioso' section is already rendered on /processo."
---

# Check — "risco silencioso" confirmado ao vivo
