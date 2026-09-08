---
type: AgentCheck
id: "2026-09-08-exciting-mccarthy-1c7t6u-check-okf-parser-baseline"
run_id: "2026-09-08-exciting-mccarthy-1c7t6u"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "pass"
---

# Check: okf-parser baseline

Run before any goal/decision/evidence was recorded, right after copying the scaffold and the four required readings.

Output: `{"concept_count": 782, "conformant": true, "diagnostics": [], "markdown_count": 785, "reserved_count": 3, "root": "/home/user/causaganha/knowledge"}`.

Conformant, 0 diagnostics. Baseline for comparison against later mid-round and final checks in this same run.
