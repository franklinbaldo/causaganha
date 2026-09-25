---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-r2xele-check-okf-parser-final"
run_id: "2026-09-25-exciting-mccarthy-r2xele"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql && uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs/2026-09-25-exciting-mccarthy-r2xele"
result: "passed"
summary: "okf-parser check conformant=true, 0 diagnostics sobre o bundle knowledge inteiro (2208 conceitos). scripts/check_agent_run_completeness.py (o gate mais estrito, que reimplementa as constraints NOT NULL/CHECK de knowledge/okf.schema.sql que okf-parser 0.45.6 ainda nao aplica) reporta os 14 documentos desta rodada (run.md + 4 readings + 1 goal + 1 decision + 3 evidence + 4 checks, incluindo este) como completos. Corrigido durante a rodada: os 3 AgentReading usavam valores de subject fora do enum declarado em okf.schema.sql (issues/prs/okf_bundle em vez de open_issues/open_prs/okf_knowledge) -- pego pelo gate estrito antes do push, nao pelo okf-parser check (que so valida metadados de chave primaria/estrangeira, nao enums de coluna)."
---

# Check: okf-parser check + gate de completude, final da rodada

```
$ uv run okf-parser check knowledge --relational-schema okf.schema.sql
{
  "concept_count": 2208,
  "conformant": true,
  "diagnostics": [],
  "markdown_count": 2211,
  "reserved_count": 3,
  "root": "/home/user/causaganha/knowledge"
}

$ uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs/2026-09-25-exciting-mccarthy-r2xele
✅ .../checks/check-pytest-full-suite.md — AgentCheck round report is complete.
✅ .../checks/check-ruff.md — AgentCheck round report is complete.
✅ .../checks/check-web-lint-typecheck.md — AgentCheck round report is complete.
✅ .../checks/check-web-test-full-suite.md — AgentCheck round report is complete.
✅ .../decisions/decision-merge-1623-defer-1605.md — AgentDecision round report is complete.
✅ .../evidence/evidence-green-manifest-url-validation-ts.md — AgentEvidence round report is complete.
✅ .../evidence/evidence-pr-1623-merged.md — AgentEvidence round report is complete.
✅ .../evidence/evidence-red-manifest-url-validation-ts.md — AgentEvidence round report is complete.
✅ .../goals/goal-manifest-url-validation-ts.md — AgentGoal round report is complete.
✅ .../readings/reading-claude-md.md — AgentReading round report is complete.
✅ .../readings/reading-issues.md — AgentReading round report is complete.
✅ .../readings/reading-okf.md — AgentReading round report is complete.
✅ .../readings/reading-prs.md — AgentReading round report is complete.
✅ .../run.md — AgentRun round report is complete.
```
