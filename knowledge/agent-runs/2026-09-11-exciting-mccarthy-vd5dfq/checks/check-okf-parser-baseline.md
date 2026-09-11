---
type: AgentCheck
id: "2026-09-11-exciting-mccarthy-vd5dfq-check-okf-parser-baseline"
run_id: "2026-09-11-exciting-mccarthy-vd5dfq"
goal_id: "2026-09-11-exciting-mccarthy-vd5dfq-goal-datajud-timezone-date-shift"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "Ran right after copying the scaffold to knowledge/agent-runs/2026-09-11-exciting-mccarthy-vd5dfq/run.md, before any goal/decision/evidence existed. Output: conformant=true, diagnostics=[], concept_count=1243, markdown_count=1246, reserved_count=3. Structural check passes even with a draft run.md, matching prior rounds' documented behavior -- the business-rule completeness gate lives in scripts/check_agent_run_completeness.py, not in okf-parser's own schema check."
---

# Check: baseline okf-parser antes de preencher o relatório

`uv run okf-parser check knowledge --relational-schema okf.schema.sql` → `conformant: true`, sem diagnósticos, com `run.md` ainda em rascunho.
