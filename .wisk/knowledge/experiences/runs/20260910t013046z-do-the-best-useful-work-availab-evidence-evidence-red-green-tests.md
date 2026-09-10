---
type: "RunEvidence"
id: "run-evidence/20260910t013046z-do-the-best-useful-work-availab/evidence-red-green-tests"
run: "runs/20260910T013046Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "uv run pytest -q tests/knowledge/test_backlog.py"
summary: "RED: with issue-1011.md's last_verified_run_id set to wisk:runs/20260910T013046Z-... before any code change, test_every_backlog_item_last_verified_run_id_resolves_to_a_real_agent_run failed (AssertionError: no knowledge/agent-runs/wisk:runs/.../run.md) and okf-parser check --relational-schema okf.schema.sql reported conformant:false with diagnostic OKF022 (BacklogItem_last_verified_run_id_id_fkey has no matching AgentRun for the wisk: value). GREEN: after dropping the REFERENCES AgentRun(id) FK from okf.schema.sql and rewriting the test as test_every_backlog_item_last_verified_run_id_resolves_to_a_real_round (accepts legacy or wisk: provenance), all 7 tests in tests/knowledge/test_backlog.py pass and okf-parser check reports conformant:true, 0 diagnostics, 1129 concepts."
goal: "run-goals/20260910t013046z-do-the-best-useful-work-availab/goal-decouple-backlog-from-agentrun"
---

# RunEvidence
