# CausaGanha v2 - Repository Preparation Summary

**Date**: 2025-12-12
**Status**: ✅ Repository prepared for v2 development
**Phase**: Phase 0 - Preparation Complete

---

## Overview

This document summarizes the repository cleanup and preparation work completed to ready CausaGanha for v2 development. The v2 refactoring will introduce PJe API integration, Ibis-based analytics, and Pydantic AI for LLM abstraction.

## What Was Done

### 1. ✅ Created v2 Directory Structure

**Location**: `/src/causaganha/v2/`

A complete directory structure was created following the architecture outlined in `/causaganha-v2-plan-from-scratch.md`:

```
src/causaganha/v2/
├── README.md              # v2 architecture documentation
├── __init__.py
├── config.py              # Configuration with Pydantic Settings (placeholder)
├── api/                   # PJe API client module
│   ├── __init__.py
│   ├── client.py          # httpx-based async API client (placeholder)
│   └── models.py          # Pydantic models for API responses (placeholder)
├── storage/               # Ibis + DuckDB data layer
│   ├── __init__.py
│   ├── connection.py      # DuckDB connection via Ibis (placeholder)
│   ├── schema.py          # Table definitions (placeholder)
│   └── queries.py         # Common analytical queries (placeholder)
├── analysis/              # Pydantic AI decision analysis
│   ├── __init__.py
│   ├── analyzer.py        # Decision analyzer (placeholder)
│   └── models.py          # DecisionAnalysis output model (placeholder)
├── pipeline/              # Data pipeline orchestration
│   ├── __init__.py
│   ├── collect.py         # Metadata collection from API (placeholder)
│   ├── analyze.py         # PDF analysis workflow (placeholder)
│   └── score.py           # Rating calculation (placeholder)
└── utils/
    ├── __init__.py
    └── logging.py         # Structured logging setup (placeholder)
```

**Purpose**: Provides a clear structure for parallel v1/v2 development without disrupting existing code.

### 2. ✅ Archived Obsolete v1 Plans

**Location**: `/docs/plans/archive/`

Created an archive directory and moved v1-specific plans that are obsolete for v2:

- ✅ `diario-class.md` → Archived (diario dataclass system - replaced by API models)
- ✅ `fix-database-integration-issues.md` → Archived (v1 database issues)
- ✅ `refactor_archive_command.md` → Archived (v1 archive command)
- ✅ `refactor-downloader-module.md` → Archived (v1 downloader module)

**Plans that remain active**:
- ✅ `MASTERPLAN.md` - Overall coordination (will be updated for v2)
- ✅ `dtb.md` - dbt-duckdb migration (still relevant)
- ✅ `multi_tribunal_collection.md` - Multi-tribunal support (relevant for v2 expansion)
- ✅ `prompt_versioning_strategy.md` - LLM prompt versioning (still needed for AI analysis)

### 3. ✅ Updated Documentation

#### CLAUDE.md
Added comprehensive v2 transition section including:
- v2 key changes overview
- Development status timeline
- v2 directory structure
- Development guidelines for v2
- Important files reference
- Updated documentation directory structure

#### README.md
Added v2 transition section in Portuguese including:
- Major v2 changes (metadata collection, data operations, LLM integration, coverage)
- v2 development status phases
- Reference to complete implementation plan

### 4. ✅ Created Supporting Documentation

- **`/src/causaganha/v2/README.md`**: Complete v2 architecture overview
- **`/docs/plans/archive/README.md`**: Explanation of archived plans
- **`/V2_PREPARATION.md`**: This summary document

---

## What Changes in v2

### Technology Stack Additions

**New Dependencies** (to be added in Phase 1):
- `pydantic-ai` - LLM provider abstraction with structured outputs
- `ibis-framework[duckdb]` - Fast analytical queries (10-100x faster than pandas)
- `httpx` - Async HTTP client for PJe API
- `structlog` - Structured logging

**To Be Removed** (in Phase 9 - Cleanup):
- Web scraping libraries (BeautifulSoup, Selenium, Scrapy) - replaced by API
- `pandas` (for analytical queries) - replaced by Ibis (may keep for other uses)

### Architecture Changes

| Component | v1 | v2 |
|-----------|----|----|
| **Metadata Collection** | Web scraping diários | PJe Communications API (JSON) |
| **Data Operations** | pandas | Ibis + DuckDB |
| **LLM Integration** | Direct Gemini SDK | Pydantic AI (provider-agnostic) |
| **Coverage** | TJRO only | 90+ courts with PJe |
| **OpenSkill Rating** | ✅ Unchanged | ✅ Unchanged |
| **PDF Analysis** | ✅ Still needed | ✅ Still needed |
| **Distribution** | ✅ Internet Archive | ✅ Internet Archive |

### Hybrid Approach

v2 uses a **hybrid approach**:
- **PJe API** provides metadata (lawyer names, OABs, process numbers, PDF links)
- **AI Analysis** still required to determine case outcomes (who won/lost)
- **OpenSkill** calculation remains unchanged

---

## Development Timeline

### Phase 0: ✅ Preparation (Current - Completed)
- Created v2 directory structure
- Archived obsolete v1 plans
- Updated documentation
- Repository ready for parallel development

### Phase 1-3: 🔄 Build v2 (Weeks 1-3) - Next
**Approach**: Test-Driven Development (TDD)
**Tasks**:
1. Implement PJe API client (tests first)
2. Build Ibis storage layer (tests first)
3. Create Pydantic AI analyzer (tests first)
4. Develop pipeline orchestration (tests first)

### Phase 4: ⏳ Integration Testing (Week 4)
- End-to-end testing
- Performance benchmarking
- Bug fixing with tests

### Phase 5: ⏳ Parallel Production (Week 5)
- Run v1 and v2 together
- Compare outputs
- Quality validation

### Phase 6: ⏳ Switchover (Week 6)
- Make v2 primary
- Keep v1 as backup
- Monitor closely

### Phase 7-8: ⏳ Expansion (Weeks 7-8)
- Add support for more courts (TJMT, etc.)
- Test cross-court rankings
- Progressive national coverage

### Phase 9: ⏳ Cleanup (Week 9)
- Archive v1 code to separate branch
- Remove unused dependencies (pandas, scrapy, etc.)
- Update all documentation
- Clean up GitHub Actions workflows

---

## Quality Standards for v2

### Non-Negotiable Requirements

1. **Test-Driven Development (TDD)**
   - Write failing tests BEFORE implementation
   - 80%+ code coverage minimum
   - No production code without tests

2. **Code Quality**
   - Zero `ruff` violations
   - Zero `mypy` type errors
   - NO `# noqa` comments allowed
   - NO `# type: ignore` comments allowed

3. **Documentation**
   - All modules must have docstrings
   - All functions must have type hints
   - Examples in docstrings for complex functions

4. **CI/CD**
   - All tests must pass before merge
   - Pre-commit hooks must pass
   - GitHub Actions must be green

---

## Next Steps

### Immediate (Week 1)
1. **Review v2 plan**: Read `/causaganha-v2-plan-from-scratch.md` completely
2. **Start with tests**: Write tests for PJe API client FIRST
3. **Implement API client**: httpx-based async client with Pydantic models
4. **Validate API access**: Test with real PJe API endpoints

### Week 2-3
1. Implement Ibis storage layer (with tests)
2. Implement Pydantic AI analyzer (with tests)
3. Build pipeline orchestration (with tests)

### Week 4+
1. Integration testing
2. Parallel production run
3. Gradual migration to v2

---

## Important Files

- **`/causaganha-v2-plan-from-scratch.md`** - Complete v2 implementation plan (103KB)
- **`/src/causaganha/v2/README.md`** - v2 architecture overview
- **`/docs/plans/archive/`** - Archived v1 plans for reference
- **`/CLAUDE.md`** - Updated with v2 development guidelines
- **`/README.md`** - Updated with v2 transition status

---

## Development Guidelines

### Parallel Development Rules

1. **v1 must keep working**: No breaking changes to existing code
2. **v2 is isolated**: All v2 code in `/src/causaganha/v2/`
3. **Shared components**: OpenSkill module can be shared
4. **Independent testing**: v1 and v2 tests can run in parallel

### Communication

- **Questions about v2**: Check `/causaganha-v2-plan-from-scratch.md` first
- **Architectural decisions**: Document in v2 module READMEs
- **Progress tracking**: Update this document as phases complete

---

## Status Checklist

### Phase 0 - Preparation ✅
- [x] Created v2 directory structure
- [x] Created placeholder module files
- [x] Archived obsolete v1 plans
- [x] Updated CLAUDE.md with v2 info
- [x] Updated README.md with v2 info
- [x] Created v2/README.md
- [x] Created V2_PREPARATION.md summary

### Phase 1 - API Client ⏳
- [ ] Write PJe API client tests
- [ ] Implement async httpx client
- [ ] Create Pydantic response models
- [ ] Test with real API endpoints
- [ ] Document API usage

### Phase 2 - Storage Layer ⏳
- [ ] Write Ibis storage tests
- [ ] Implement DuckDB connection
- [ ] Define table schemas
- [ ] Create common queries
- [ ] Benchmark vs pandas

### Phase 3 - Analysis ⏳
- [ ] Write decision analyzer tests
- [ ] Implement Pydantic AI agent
- [ ] Create DecisionAnalysis model
- [ ] Test with sample PDFs
- [ ] Tune prompts

---

## Conclusion

✅ **Repository is ready for v2 development!**

The v2 directory structure is in place, obsolete plans are archived, and documentation is updated. The project can now proceed with parallel v1/v2 development following the TDD approach outlined in the comprehensive v2 plan.

**Next milestone**: Complete Phase 1 (PJe API Client implementation) with full TDD coverage.
