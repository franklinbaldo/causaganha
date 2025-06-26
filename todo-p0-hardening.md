# P0 Hardening Tasks - Critical Infrastructure Fixes

**Branch**: `feature/p0-hardening`  
**Priority**: P0 (Immediate - Week 1)  
**Effort**: ~1.5 days total

## Tasks Overview

### 1. Fusionar Workflows ⏱️ ½ day
- [ ] Create unified `pipeline.yml` workflow
- [ ] Use `needs:` dependencies for job sequencing: collect → archive → extract → update → backup
- [ ] Share artifacts between jobs to avoid redundant work
- [ ] Remove individual workflow files (01_collect.yml, 02_extract.yml, 03_update.yml, 04_backup_r2.yml)
- [ ] Keep test.yml separate for PR validation
- [ ] Update CLAUDE.md documentation

### 2. Migrations Versionadas ⏱️ 1 day  
- [ ] Create `migrations/` directory structure
- [ ] Extract DDL from `database.py` to `migrations/001_init.sql`
- [ ] Create migration runner in `causaganha/core/migration_runner.py`
- [ ] Add version tracking table (`schema_version`)
- [ ] Update `CausaGanhaDB` to use migration runner instead of inline DDL
- [ ] Test migration runner with existing database
- [ ] Document migration process in CLAUDE.md

### 3. Remover `except Exception` ⏱️ 2-3 hours
- [ ] Find all generic exception handlers: `grep -R "except Exception"`
- [ ] Replace with specific exceptions:
  - `FileNotFoundError` for file operations
  - `JSONDecodeError` for JSON parsing
  - `DuckDBError` for database operations  
  - `requests.RequestException` for HTTP calls
- [ ] Let critical errors propagate to fail fast
- [ ] Update tests to verify specific exception handling

### 4. Refatorar Logging ⏱️ 2 hours
- [ ] Find f-string usage in logging: `grep -R "logger.*f\""`
- [ ] Replace with lazy evaluation: `logger.info("Processing %s", filename)`
- [ ] Configure ruff with `TRY003` rule
- [ ] Run ruff check and fix remaining issues
- [ ] Update logging best practices in CLAUDE.md

## Success Criteria

- [ ] All workflows consolidated into single pipeline
- [ ] Database schema versioned and migration-ready
- [ ] No generic `except Exception:` blocks remain
- [ ] All logging uses lazy evaluation
- [ ] CI passes all tests
- [ ] Documentation updated

## Files to Modify

### New Files
- `migrations/001_init.sql`
- `causaganha/core/migration_runner.py` 
- `.github/workflows/pipeline.yml`

### Modified Files  
- `causaganha/core/database.py` (remove inline DDL)
- `causaganha/core/extractor.py` (specific exceptions)
- `causaganha/core/downloader.py` (specific exceptions)
- `causaganha/core/pipeline.py` (logging + exceptions)
- `CLAUDE.md` (updated workflows docs)

### Removed Files
- `.github/workflows/01_collect.yml`
- `.github/workflows/02_extract.yml` 
- `.github/workflows/03_update.yml`
- `.github/workflows/04_backup_r2.yml`

## Testing Strategy

1. Run full pipeline locally with migrations
2. Verify exception handling doesn't mask real errors
3. Check logging performance improvements
4. Ensure CI completes successfully

---

**Next Phase**: After P0 completion, move to `feature/p1-data-architecture` for database normalization.