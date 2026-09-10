---
type: "RunDecision"
id: "run-decisions/20260910t182322z-do-the-best-useful-work-availab/decision-remove-dead-warnings-field"
run: "runs/20260910T182322Z-do-the-best-useful-work-available-in-this-reposi"
question: "scripts/ia_practicality_probe.py's probe_parquet() declares result['warnings'] but never populates it, so report['warnings'] is always 0. Should a genuine warning condition be implemented, or should the dead field be removed?"
decision: "Remove the dead field entirely (result['warnings'], the 'if result[\"warnings\"]:' check, and report['warnings']) rather than invent a new warning condition."
rationale: "The two candidate warning conditions considered don't hold up: (1) 'extra columns beyond MINIMAL_REQUIRED_COLUMNS' would fire for almost every real table (comunicacoes/textos/etc. all have dozens of columns beyond the 1-3 minimal ones checked), making it pure noise rather than a meaningful signal; (2) a 'suspiciously low row count' threshold would be an arbitrary number invented with no observed data to justify it, the exact kind of speculative feature CLAUDE.md's project instructions warn against ('Don't add features... beyond what the task requires'). A declared-but-dead field that implies a monitoring signal exists when it doesn't is worse than no field at all -- it's actively misleading to a human reading the JSON report. If a genuine warning condition is identified later from real probe data, it can be added then with actual justification."
goal: "run-goals/20260910t182322z-do-the-best-useful-work-availab/goal-decide-ia-probe-warnings"
alternatives: ["Implement 'extra columns present' as a warning condition", "Implement a hardcoded low-row-count threshold as a warning condition"]
---

# RunDecision
