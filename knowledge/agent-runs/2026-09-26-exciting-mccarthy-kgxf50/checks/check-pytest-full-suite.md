---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-kgxf50-check-pytest-full-suite"
run_id: "2026-09-26-exciting-mccarthy-kgxf50"
goal_id: "2026-09-26-exciting-mccarthy-kgxf50-goal-1051-test-split-adjudication"
command: "uv run pytest -q"
result: "observed"
evidence_id: "2026-09-26-exciting-mccarthy-kgxf50-evidence-reviews-ingested"
summary: "Full repository suite: exit code 0, exactly 1 failure -- tests/test_check_agent_run_completeness.py::test_main_over_this_rounds_own_report_tree_is_complete -- caused entirely by this round's own run.md still being a draft (completed_at/next_move empty) at the time this check ran, exactly as documented by the scaffold. The detailed per-file report from that test pinpointed 3 additional enum-field typos in this round's own OKF files (AgentCheck.result='pass' should be 'passed', AgentEvidence.kind='runtime_observation' should be 'runtime', AgentGoal.status='in_progress' should be 'active'/'achieved') -- fixed immediately after this check, before the final okf-parser/completeness re-check."
---

# Check: full repository test suite (pre-finalization)

```
$ uv run pytest -q
... (462 files, full suite)
FAILED tests/test_check_agent_run_completeness.py::test_main_over_this_rounds_own_report_tree_is_complete
[exited with code 0]
```

Re-running just that test in isolation printed the per-file report, which
caught 3 real enum-value mistakes in this round's own OKF frontmatter
(not just the expected draft-run.md gap) -- fixed via the fields'
declared enums (`AgentCheck.result`, `AgentEvidence.kind`,
`AgentGoal.status`) in `scripts/check_agent_run_completeness.py`.
