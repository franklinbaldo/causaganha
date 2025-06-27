# CausaGanha Documentation

Welcome to the official CausaGanha documentation - a distributed judicial analysis platform.

## User Guides
- [Quickstart Guide](quickstart.md) - Get started with the modern CLI
- [CLI Design](cli_design.md) - Complete command reference and architecture
- [FAQ](faq.md) - Frequently asked questions and known limitations

## System Architecture
- [Internet Archive Discovery Guide](ia_discovery_guide.md) - Discover and list archived judicial documents
- [OpenSkill Implementation](openskill.md) - Rating system for lawyer performance evaluation
- [Business Rules](Business_rules.md) - System business logic and rules
- [Prompt Versioning Strategy](prompt_versioning_strategy.md) - LLM prompt management and versioning

## Current System Status

✅ **Modern CLI System Operational** (2025-06-27)
- **4-stage pipeline**: queue → archive → analyze → score
- **Modern Typer CLI** with rich progress display and error handling
- **OpenSkill rating system** for lawyer performance evaluation
- **Shared DuckDB database** via Internet Archive with conflict prevention
- **Domain validation** (.jus.br only) for security
- **Resume capability** for interrupted processing
- **Database management** with migrate, sync, backup, and reset operations
- **Concurrent processing** with configurable limits and rate limiting

## Quick Start

```bash
# Install and setup
uv sync --dev
uv run --env-file .env causaganha db migrate

# Queue judicial documents (.jus.br domains only)
uv run --env-file .env causaganha queue --from-csv diarios.csv

# Run full pipeline
uv run --env-file .env causaganha pipeline --from-csv diarios.csv

# Monitor progress
uv run --env-file .env causaganha stats
```

See the [Quickstart Guide](quickstart.md) for detailed setup instructions.
