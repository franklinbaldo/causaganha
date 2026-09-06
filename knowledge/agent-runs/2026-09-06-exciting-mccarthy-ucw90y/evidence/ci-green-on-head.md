---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-ucw90y-evidence-ci-green-on-head"
run_id: "2026-09-06-exciting-mccarthy-ucw90y"
goal_id: "2026-09-06-exciting-mccarthy-ucw90y-goal-review-pr-1169"
kind: "ci"
reference: "https://github.com/franklinbaldo/causaganha/actions/runs/34002426772 (CI/test.yml), /34002426765 (Agents Surface Visual Capture), /34002426768 (Product Surface Visual Capture) — all head_sha=385970171515f6f33e42a4ec6083b895c93170ea"
summary: "actions_list(list_workflow_runs, branch=reboot/cobogo-web) shows all three merge-gate workflows named in PR #1169's own body (CI, Product Surface Visual Capture, Agents Surface Visual Capture) completed with conclusion=success on the exact current head commit. Earlier commits on the same branch (82b6a673, 3744f677) show CI conclusion=failure, later fixed by subsequent commits — the PR's history includes real red-to-green iteration, not an untested branch."
---

# Evidência — CI verde no head atual da PR #1169

Os três workflows de gate (CI, captura visual de produto, captura visual de agentes) estão `success` no sha atual; commits anteriores da mesma branch mostram falhas reais corrigidas depois.
