---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-qnpypw-check-okf-parser"
run_id: "2026-09-05-exciting-mccarthy-qnpypw"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "Run three times this round: (1) before any round files existed, bundle conformant (0 diagnostics); (2) after copying the scaffold and writing the four readings, correctly flagged 3 dangling AgentReading.run_id foreign keys because run.md was still the empty scaffold; (3) after filling run.md with real goal/decision/evidence/check ids, bundle conformant again (0 diagnostics)."
---

# Check: `okf-parser check` usado ao longo da rodada
