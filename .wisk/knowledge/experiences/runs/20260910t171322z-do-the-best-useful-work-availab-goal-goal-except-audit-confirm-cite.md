---
goal: "Perform the confirm-and-cite pass named by the wiki's own next_move on the last 3 bare except-Exception sites (batch_embed_decisions.py x3, build_gold_benchmark.py x1, daily_benchmark_update.py x1), verifying each site's noqa reasoning still holds against docs/adr/0011's substantive test before citing, rather than mechanically adding the citation."
id: "run-goals/20260910t171322z-do-the-best-useful-work-availab/goal-except-audit-confirm-cite"
kind: "task-advance"
rationale: "This is the last work needed to fully close the except-Exception scoped-audit lineage (PR series #1289-#1429) across the entire repository. The wiki's own recorded next_move called this 'a lighter confirm-and-cite pass' -- verifying that framing rather than assuming it is exactly the discipline the lineage itself established (paragraph 41's own lesson: a passing enforcement test only proves compliance within whatever it actually checks)."
run: "runs/20260910T171322Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "Each of the 3 files' sites is classified correctly per direct verification (loop-over-many-independent-units + full-traceback-capture for cite; single-shot/poll-one-resource for narrow), tests/test_except_exception_policy.py enforces the classification, full ruff+pytest green, PR opened."
type: "RunGoal"
---

# RunGoal
