# Legacy Scripts

This directory contains v1-specific scripts that are no longer needed for v2 development.

## Why These Are Archived

CausaGanha v2 replaces many v1 utilities:
- **Web scraping utilities** → Replaced by PJe API client
- **Pandas-based analytics** → Replaced by Ibis
- **Manual discovery tools** → Replaced by API-based collection

## Archived Scripts

### Discovery Tools (v1)
- `bulk_discovery.py` - Bulk IA discovery (v1-specific)
- `manual_discovery.py` - Manual IA discovery (v1-specific)

### Tribunal Tools (v1)
- `check_tribunal_registry.py` - v1 tribunal registry checks

### Data Migration (v1)
- `migrate_existing_pii.py` - v1 PII migration utilities
- `decode_pii_tool.py` - v1 PII decoding tool

### Maintenance (v1)
- `update_prompt_hashes.py` - v1 prompt versioning
- `run_analytics.py` - v1 analytics runner
- `run_all_tests.sh` - v1 test runner
- `check_environment.py` - v1 environment checks

### Environment Checks (v1)
- `env/` - v1 environment validation scripts

## Active Scripts

See `/scripts/` for scripts that remain active:
- `dev/` - Development tools (still needed)
- `db/` - Database management scripts
- `setup_dev.sh` - Development environment setup

## Reference Value

These scripts are kept for:
- Understanding v1 workflows
- Migrating any remaining v1 data
- Historical reference
