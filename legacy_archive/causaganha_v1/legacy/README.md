# Legacy v1 Code

This directory is reserved for v1 code during the transition to v2.

## Current Status

**Phase 0 - Preparation**: v1 code currently remains in `/src/` for compatibility.

## Migration Plan

During **Phase 9 (Cleanup - Week 9)**, v1 code will be:
1. Moved to a separate git branch `archive/v1`
2. v1 code in `main` branch will be removed
3. Only v2 code will remain in the main branch

## Current v1 Code Location

v1 code currently resides in `/src/`:
- `cli.py` - v1 CLI interface
- `async_diario_pipeline.py` - v1 async pipeline
- `database.py` - v1 database layer
- `extractor.py` - v1 Gemini extractor
- `ia_discovery.py` - v1 IA discovery
- `ia_helpers.py` - v1 IA helpers
- `openskill_rating.py` - **Shared with v2** (unchanged)
- `pipeline.py` - v1 legacy orchestrator
- `archive_db.py` - v1 database archive
- `pii_manager.py` - v1 PII management
- `security_audit.py` - v1 security
- `security_utils.py` - v1 security utils
- `simple_backup.py` - v1 backup
- `anonymization_hooks.py` - v1 anonymization
- `config.py` - v1 configuration
- `utils.py` - v1 utilities
- `models/` - v1 data models
- `tribunais/` - v1 tribunal adapters
- `utils/` - v1 utility modules

## Why Not Move Now?

Moving v1 code now would require:
1. Updating all import statements across the codebase
2. Updating tests to use new import paths
3. Updating CLI entry points in pyproject.toml
4. Risk of breaking v1 functionality during v2 development

The v2 plan calls for **parallel development** where v1 continues to work while v2 is built. Therefore, v1 code remains in its current location until v2 is production-ready.

## Shared Components

Some components will be shared between v1 and v2:
- `openskill_rating.py` - Rating algorithm (unchanged)
- DuckDB database (shared storage)
- Internet Archive integration (shared distribution)

## Next Steps

This directory will be populated during Phase 9 when v2 becomes the primary implementation and v1 is archived to a separate branch.
