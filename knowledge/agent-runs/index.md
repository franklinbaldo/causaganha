# Agent runs

One directory per hourly-loop round, named `<run-id>/`, holding a typed `AgentRun` report and its supporting `Agent*` documents (`readings/`, `goals/`, `decisions/`, `evidence/`, `checks/`). See `.claude/hourly-loop.md` for how a round builds this tree and `.claude/agent-run-scaffold.md` for the starting scaffold.

`scripts/check_agent_run_completeness.py` validates this whole tree — run it directly with a directory argument, or let CI run it via `.github/workflows/okf.yml` on every PR touching `knowledge/**`:

```bash
uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs
```

`uv run okf-parser check knowledge --relational-schema okf.schema.sql` validates structural (primary-key/foreign-key) integrity across the whole `knowledge/` bundle, including this tree, but does not enforce the `NOT NULL`/`CHECK` completeness contract declared per `Agent*` table in `knowledge/okf.schema.sql` — that is what the completeness checker above is for.
