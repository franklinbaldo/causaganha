---
type: AgentDecision
id: "2026-09-05-exciting-mccarthy-qvwrkl-decision-scaffold-completed-at-clarification"
run_id: "2026-09-05-exciting-mccarthy-qvwrkl"
goal_id: "2026-09-05-exciting-mccarthy-qvwrkl-goal-publicacoes-copy-reference"
question: "This round's PR #1153 hit a real CI failure because completed_at was left empty while the PR was open (see evidence/ci-red-completed-at.md). Should the scaffold's guidance change so a future round does not repeat the same RED cycle?"
choice: "Added one paragraph to .claude/agent-run-scaffold.md making explicit that completed_at may only stay empty during local drafting — any commit that gets pushed (which opens or updates the PR) must already carry a real completed_at timestamp, since scripts/check_agent_run_completeness.py runs in CI over the whole knowledge/agent-runs/ tree including in-flight rounds. Clarified that completed_at marks when this session's active work concluded, not when the PR is merged, so result_state/result_summary/next_move can still be revised in a follow-up commit without touching completed_at."
rationale: "The scaffold's YAML defaults (completed_at: \"\") are correct for the mid-session drafting stage the scaffold describes, but say nothing about the moment before a push — and the CI-enforced completeness contract (built by an earlier round specifically to catch this class of gap) does not distinguish 'still drafting locally' from 'pushed as part of an open PR'. Leaving the scaffold silent on this cost this round one full CI cycle for a self-inflicted, entirely avoidable failure. This is a one-line, low-risk documentation fix — no schema or type change is warranted, since the underlying NOT NULL contract on completed_at was already correct and doing its job; only the operator-facing guidance was incomplete."
---

# Decisão: esclarecer `completed_at` no scaffold do AgentRun

Documentação corrigida para prevenir a mesma falha de CI que esta rodada sofreu e corrigiu.
