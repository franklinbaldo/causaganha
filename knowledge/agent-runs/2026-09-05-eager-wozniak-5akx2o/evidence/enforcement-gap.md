---
type: AgentEvidence
id: "2026-09-05-eager-wozniak-5akx2o-evidence-enforcement-gap"
run_id: "2026-09-05-eager-wozniak-5akx2o"
goal_id: "2026-09-05-eager-wozniak-5akx2o-goal-enforce-completeness"
kind: "okf"
reference: "okf_parser/relational_schema.py:parse_relational_schema; okf_parser/declared_schema.py:DeclaredSchema; okf_parser/typed_tables.py:materialize_typed_tables (okf-parser 0.45.6, site-packages)"
summary: "Direct source inspection plus a scratch repro (temp bundle with a CHECK-constrained AgentRun spec and an all-empty instance) confirmed both validation paths silently accept an empty AgentRun: `check --relational-schema` only reads PRIMARY KEY/UNIQUE/FOREIGN KEY rows from duckdb_constraints(), and `compile_types` discards every constraint, keeping only `columns: dict[str, DuckDBLogicalType]` before re-creating the materialized table from bare types. Running `okf-parser check knowledge --relational-schema okf.schema.sql` against the copied, all-empty .claude/agent-run-scaffold.md reproduced this live: conformant: true, 0 diagnostics."
---

# Evidência: lacuna de enforcement no okf-parser pinado
