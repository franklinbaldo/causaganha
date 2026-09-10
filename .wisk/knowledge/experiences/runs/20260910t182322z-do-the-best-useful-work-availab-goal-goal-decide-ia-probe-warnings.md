---
goal: "Resolve the dead result['warnings']/report['warnings'] field in scripts/ia_practicality_probe.py's probe_parquet()/main(), flagged by a prior round as needing a deliberate implement-or-remove decision, then add test coverage (this file has none)."
id: "run-goals/20260910t182322z-do-the-best-useful-work-availab/goal-decide-ia-probe-warnings"
kind: "task-advance"
rationale: "Named as a specific, still-open lead in handoffs/handoff-pr-1434-awaiting-ci and the wiki's long-tail-audit entries: result['warnings'] is declared but never populated anywhere in probe_parquet(), so report['warnings'] is always 0 -- silently promising a monitoring signal that doesn't exist."
run: "runs/20260910T182322Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "A decision is made and recorded (implement a genuine warning condition, or remove the dead field), the code matches the decision, a test demonstrates the fix, full ruff+pytest green, PR opened."
type: "RunGoal"
---

# RunGoal
