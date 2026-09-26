---
type: AgentDecision
id: "2026-09-26-exciting-mccarthy-6m3b2b-decision-merge-not-rebase"
run_id: "2026-09-26-exciting-mccarthy-6m3b2b"
decision: "Reconcile PR #1678 against main with a merge commit (git merge origin/main on the PR's own branch), not a rebase, and keep both round's regression-guard test functions as separate, additive tests rather than collapsing them into one."
reason: "The branch (claude/exciting-mccarthy-pg2bcv) is not owned by this session and already has an open PR with review activity (a Codex bot comment); rewriting its history with a rebase would force-push over that PR's existing commits, which the repo's own PR-driving rules treat as a last resort requiring explicit authorization. A merge commit resolves the conflict without rewriting anything already pushed. Keeping both test functions (test_real_store_reflects_1051_uq3be8_round_adjudication and test_real_store_reflects_1051_pg2bcv_round_adjudication) as separate assertions, each checking its own five/three document ids and its own pre-round count threshold, preserves both rounds' regression-guard value -- collapsing them into one would lose the ability to detect which specific batch's documents went missing if the store were ever reverted."
---

# Decision: merge commit, keep both regression guards
