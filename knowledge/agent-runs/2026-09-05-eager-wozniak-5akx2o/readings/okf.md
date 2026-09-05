---
type: AgentReading
id: "2026-09-05-eager-wozniak-5akx2o-reading-okf"
run_id: "2026-09-05-eager-wozniak-5akx2o"
subject: "okf_knowledge"
reference: "knowledge/okf.schema.sql (AgentRun table); okf_parser.relational_schema.parse_relational_schema; okf_parser.declared_schema.DeclaredSchema; okf_parser.typed_tables.materialize_typed_tables"
finding: "PR #1141's AgentRun table declares NOT NULL and CHECK constraints meant to make an incomplete round report fail validation. But okf-parser 0.45.6 (the pinned version) never enforces them: `check --relational-schema` (relational_schema.py) reads only PRIMARY KEY/UNIQUE/FOREIGN KEY rows from duckdb_constraints(), skipping CHECK entirely; and `compile_types` (typed_relations.py -> typed_tables.py) rebuilds each declared table from `DeclaredSchema.columns: dict[str, DuckDBLogicalType]` — bare column types read back from the catalog after the .schema.sql ran once, with every constraint discarded. Reproduced directly: copying .claude/agent-run-scaffold.md into knowledge/agent-runs/<run-id>/run.md (every required field empty) and running `okf-parser check knowledge --relational-schema okf.schema.sql` still reports `conformant: true` with zero diagnostics. This is the concrete gap this round closes."
---

# Leitura de conhecimento OKF

O contrato declarado no SQL é hoje apenas documentação — nada no okf-parser pinado o executa contra os dados. Sem um checador próprio, o scaffold "nasce inválido" não é verdade: ele nasce e permanece formalmente válido, mesmo vazio.
