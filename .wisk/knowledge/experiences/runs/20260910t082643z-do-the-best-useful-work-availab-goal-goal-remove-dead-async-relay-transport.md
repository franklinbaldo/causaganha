---
goal: "Delete common.relay's AsyncRelayTransport class and async_relay_transport_from_env function (confirmed zero production callers anywhere in src/ or scripts/ via repo-wide grep) via RED->GREEN TDD, open a PR, and drive it to merge."
id: "run-goals/20260910t082643z-do-the-best-useful-work-availab/goal-remove-dead-async-relay-transport"
kind: "task-advance"
rationale: "Explicit next_move from run 20260910T064722Z's RunOutcome: this exact candidate was flagged as 'genuinely dead code, worth a repo-wide grep before removing' but deliberately deferred. Repo-wide grep now confirms only the definition module (src/common/relay.py) and its own test file (tests/common/test_relay.py) reference these two symbols -- no sync or async DJEN/STJ/TJRO/TSE client uses them. This matches the established dead-code-with-zero-callers pattern already fixed five times in this loop's lineage (candidates.py, coverageInsights.ts Catalog surface, datajud/models.py's data14_bound, TribunalCoverageGrid.astro, velocityCalc.ts)."
run: "runs/20260910T082643Z-do-the-best-useful-work-available-in-this-reposi"
status: "carried_forward"
success_signal: "Full pytest suite green and ruff clean after removal, plus a module-surface regression-guard test (mirroring PR #1332's pattern) asserting AsyncRelayTransport/async_relay_transport_from_env are absent from common.relay's public surface, so the dead symbol cannot silently reappear."
type: "RunGoal"
---

# RunGoal
