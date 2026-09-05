---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-1fxd8b-evidence-pr-1154-merge"
run_id: "2026-09-05-exciting-mccarthy-1fxd8b"
goal_id: "2026-09-05-exciting-mccarthy-1fxd8b-goal-evidence-matrix"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1154 (merged as 0b80890)"
summary: "All 11 check runs on the final head (16f139e) passed: validate, tests (tjro), web, compare-product-surfaces, lint, CodeQL (4 languages), GitGuardian. Two check_run.completed failure events arrived for an earlier, already-superseded commit (7aa0fd9) — both traced to the same root cause (run.md missing completed_at, caught by the repo's own okf/AgentRun-completeness gates in both the 'validate' workflow and tests/test_check_agent_run_completeness.py), already fixed by the follow-up commit before those stale notifications were even read. mergeable_state was 'clean', no open review threads, no Claude Approvals check configured in this repository (not applicable). Squash-merged into main (repo convention: no merge commits in main's history) as 0b80890, closing issue #1130."
---

# Evidência: PR #1154 mesclada

https://github.com/franklinbaldo/causaganha/pull/1154 → squash-merged como `0b80890` em `main`, fechando a issue #1130.
