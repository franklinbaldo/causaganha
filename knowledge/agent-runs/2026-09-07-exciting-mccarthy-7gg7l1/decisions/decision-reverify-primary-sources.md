---
type: AgentDecision
id: "2026-09-07-exciting-mccarthy-7gg7l1-decision-reverify-primary-sources"
run_id: "2026-09-07-exciting-mccarthy-7gg7l1"
goal_id: "2026-09-07-exciting-mccarthy-7gg7l1-goal-reconcile-backlog"
question: "knowledge/backlog/'s 17 items were all last verified within the previous ~12 hours and their blocking_reason text looked unchanged — is re-reading that same text enough to refresh last_verified_run_id/last_verified_at, or does 'verified' require an independent primary-source check this round?"
choice: "Require an independent primary-source check per category before refreshing any file: env grep for IA/GPU/ML credentials (credentials, ml_data_work), a GitHub Actions run-history query for deploy-mcp.yml (infra_decision), a live curl to cdn.tse.jus.br (network_access), and a fresh GitHub open-issues list compared 1:1 against the cached files (deprioritized_by_owner and overall coverage)."
rationale: "knowledge/backlog/index.md's own instruction is to reopen investigation only if the issue changed state on GitHub, the environment changed, or last_verified_at is stale — but it does not define a floor for how fresh 'not stale' needs to be, and re-reading the same comment thread a previous round already summarized does not detect an environment change (a credential appearing, a manual workflow_dispatch run) that leaves no trace in the issue thread itself. tests/knowledge/test_backlog.py's own docstring records that a similar failure already happened once (issue #985's blocking_reason drifted to the wrong template and survived two re-verification rounds because they only re-checked the recorded reason's own premise, not the issue's actual scope) — the fix there was a pinning test, not a promise to read more carefully. Applying the same lesson here: a primary-source check is strictly more reliable than re-reading cached prose, costs a handful of cheap read-only calls, and is the only way this round could truthfully claim the backlog is still accurate rather than merely unchanged in wording."
---

# Decisão: exigir reverificação por fonte primária, não releitura do cache

Renovar `last_verified_run_id`/`last_verified_at` só depois de checar cada categoria de bloqueio contra uma fonte primária (env, GitHub Actions, rede, lista de issues) nesta própria rodada — não apenas reler o texto que a rodada anterior já tinha escrito.
