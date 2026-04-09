# CausaGanha Python package

This directory contains the main Python package used by the CLI, data pipeline, analysis workflows, and storage layers.

## Package layout

```text
src/causaganha/
  analysis/      AI analysis, embeddings, RAG, and ground truth utilities
  archival/      archival and cold storage helpers
  catalog/       catalog generation logic
  cli/           Typer CLI entrypoints and commands
  clients/       external service clients
  compliance/    compliance reporting
  pipeline/      collection, export, analysis, and orchestration workflows
  scoring/       OpenSkill rating logic
  storage/       DuckDB, schema, migrations, and repositories
  config.py      shared configuration
```

## What is here today

The package currently exposes the `causaganha` CLI and supports these main areas:

- collection from PJe and DJEN-related sources
- backfill and archival workflows
- Parquet export and downstream analysis
- OpenSkill-based scoring
- DuckDB-backed local data handling
- AI-assisted analysis and embedding flows

## CLI entrypoint

The package installs the `causaganha` command defined by the project metadata in [pyproject.toml](/Users/frank/workspace/causaganha/pyproject.toml).

Inspect the current CLI surface with:

```bash
uv run causaganha --help
```

## Notes for maintainers

- Keep this file aligned with the actual module tree.
- If a directory is removed or renamed, update this file in the same change.
- Prefer pointing readers to concrete modules and commands instead of aspirational architecture.
