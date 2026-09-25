---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-akb9oz-check-okf-parser-final"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql && uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs/2026-09-25-exciting-mccarthy-akb9oz"
result: "passed"
summary: "okf-parser check conformant=true, 0 diagnostics sobre o bundle knowledge inteiro (2237 conceitos). scripts/check_agent_run_completeness.py (o gate mais estrito, que reimplementa as constraints NOT NULL/CHECK de knowledge/okf.schema.sql) reporta os 15 documentos desta rodada (run.md + 4 readings + 1 goal + 2 decisions + 3 evidence + 5 checks, incluindo este) como completos."
---

# Check: okf-parser check + gate de completude, final da rodada

```
$ uv run okf-parser check knowledge --relational-schema okf.schema.sql
{
  "concept_count": 2237,
  "conformant": true,
  "diagnostics": [],
  "markdown_count": 2240,
  "reserved_count": 3,
  "root": "/home/user/causaganha/knowledge"
}

$ uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs/2026-09-25-exciting-mccarthy-akb9oz
✅ .../checks/check-pytest-full-suite.md — AgentCheck round report is complete.
✅ .../checks/check-ruff.md — AgentCheck round report is complete.
✅ .../checks/check-web-build.md — AgentCheck round report is complete.
✅ .../checks/check-web-lint-typecheck.md — AgentCheck round report is complete.
✅ .../checks/check-web-test-full-suite.md — AgentCheck round report is complete.
✅ .../decisions/decision-merge-1627-select-1613.md — AgentDecision round report is complete.
✅ .../decisions/decision-shared-csp-constant.md — AgentDecision round report is complete.
✅ .../evidence/evidence-green-csp-xss-floor.md — AgentEvidence round report is complete.
✅ .../evidence/evidence-pr-1627-merged.md — AgentEvidence round report is complete.
✅ .../evidence/evidence-red-csp-xss-floor.md — AgentEvidence round report is complete.
✅ .../goals/goal-csp-xss-floor.md — AgentGoal round report is complete.
✅ .../readings/reading-claude-md.md — AgentReading round report is complete.
✅ .../readings/reading-issues.md — AgentReading round report is complete.
✅ .../readings/reading-okf.md — AgentReading round report is complete.
✅ .../readings/reading-prs.md — AgentReading round report is complete.
✅ .../run.md — AgentRun round report is complete.
```
