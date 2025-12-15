# CausaGanha V2 Implementation Plan - From Scratch

![Status](https://img.shields.io/badge/status-in_progress-yellow?style=for-the-badge)
![Version](https://img.shields.io/badge/version-2.0-blue?style=for-the-badge)

> 📋 **IMPLEMENTATION PLAN**: Comprehensive guide for CausaGanha V2 development, tracking progress from foundation to production-ready system.

**Last Updated**: 2025-12-15
**Current Phase**: Phase 2 - Core Pipeline Implementation
**Test Status**: 33/33 passing (85% coverage)

---

## 🎯 Project Overview

CausaGanha V2 is a complete rewrite of the judicial decision analysis platform. The system extracts, analyzes, and scores judicial decisions from Brazilian tribunals (starting with TJRO) using Google's Gemini LLM and local DuckDB storage.

### Key Technologies

- **Language**: Python 3.11+
- **CLI Framework**: Typer
- **Async Runtime**: asyncio + httpx
- **Database**: DuckDB + Ibis
- **LLM**: Google Gemini (Pydantic AI)
- **Logging**: structlog
- **Testing**: pytest

### Architecture Style

Modular Monolith with Hexagonal Architecture principles:

- **Domain Layer**: Pure business logic (`src/causaganha/domain/`, `src/causaganha/analysis/`)
- **Application Layer**: Orchestration (`src/causaganha/pipeline/`)
- **Infrastructure Layer**: External systems (`src/causaganha/storage/`, `src/causaganha/api/`)
- **Interface Layer**: CLI (`src/causaganha/cli.py`)

---

## 📊 Current Status

### ✅ Completed Components

#### 1. **Foundation (Phase 1)**

- [x] Project structure established
- [x] Database schema with DuckDB
- [x] Repository pattern implementation
- [x] Basic CLI framework with Typer
- [x] Configuration management
- [x] Structured logging with structlog

#### 2. **API Integration**

- [x] PJe API client with httpx
- [x] Pydantic schemas for data validation
- [x] Async request handling
- [x] Error handling for API calls

#### 3. **Storage Layer**

- [x] Ibis-based data layer
- [x] DuckDB connection management
- [x] Repository pattern for intimations
- [x] Schema creation and management
- [x] Query abstractions

#### 4. **Analysis Pipeline**

- [x] Pydantic AI decision analyzer
- [x] Gemini LLM integration
- [x] Decision analysis models
- [x] Document service structure

#### 5. **Scoring System**

- [x] OpenSkill rating implementation
- [x] Rating model with Pydantic
- [x] Score calculation pipeline
- [x] Rating persistence

#### 6. **CLI Commands**

- [x] `causaganha collect` - Collect intimations from PJe
- [x] `causaganha analyze` - Analyze decisions using LLM
- [x] `causaganha db init` - Initialize database schema
- [x] `causaganha db status` - Show database status
- [ ] `causaganha archive` - Placeholder (not implemented)
- [ ] `causaganha score` - Missing
- [ ] `causaganha pipeline` - Missing

#### 7. **Testing**

- [x] 33 tests passing (85% coverage)
- [x] Unit tests for core components
- [x] Integration tests for pipelines
- [x] Repository tests

### 🔧 In Progress

#### Phase 2: Core Pipeline Implementation

1. **Archive Command Implementation**
   - Integrate with Internet Archive
   - Download and archive diarios
   - Support for batch operations

2. **Score Command Implementation**
   - CLI interface for scoring
   - Integration with scoring pipeline
   - Rating calculations and persistence

3. **Pipeline Orchestration**
   - Unified pipeline command
   - End-to-end workflow: collect → analyze → score
   - Error recovery and resume capability

### 📋 Pending Components

#### Phase 3: Production Features

1. **Advanced Database Operations**
   - `db migrate` - Schema migrations
   - `db sync` - Sync with Internet Archive
   - `db backup` - Database backup/restore

2. **Enhanced Error Handling**
   - Retry logic with exponential backoff
   - Detailed error reporting
   - Recovery mechanisms

3. **Configuration Management**
   - Environment-based configuration
   - API key management
   - Logging level configuration

4. **Documentation**
   - API documentation
   - User guides
   - Development guides

---

## 🏗️ Implementation Phases

### Phase 1: Foundation ✅ COMPLETED

**Objective**: Establish core infrastructure and basic CLI

**Delivered**:
- Project structure and packaging
- Database layer with DuckDB
- Repository pattern
- Basic CLI commands
- Testing framework

**Test Coverage**: 85% (33/33 tests passing)

### Phase 2: Core Pipeline 🔄 IN PROGRESS

**Objective**: Implement complete data collection and analysis pipeline

**Timeline**: Current phase (1-2 weeks)

#### Week 1: Pipeline Commands

**Tasks**:

1. **Implement Archive Command** (2-3 days)
   - [ ] Create archive pipeline module
   - [ ] Integrate with Internet Archive client
   - [ ] Add CLI command with options (limit, dry-run)
   - [ ] Write integration tests
   - [ ] Update documentation

2. **Implement Score Command** (1-2 days)
   - [ ] Add score CLI command
   - [ ] Connect to scoring pipeline
   - [ ] Add filtering and batch options
   - [ ] Write tests
   - [ ] Document usage

3. **Pipeline Orchestration Command** (2-3 days)
   - [ ] Create unified pipeline orchestrator
   - [ ] Implement collect → analyze → score workflow
   - [ ] Add resume capability for interrupted runs
   - [ ] Error handling and logging
   - [ ] Comprehensive testing

#### Week 2: Enhancement and Testing

**Tasks**:

1. **Enhanced Error Handling** (2 days)
   - [ ] Retry logic for API calls
   - [ ] Graceful degradation
   - [ ] Detailed error messages
   - [ ] Recovery mechanisms

2. **Logging and Monitoring** (1 day)
   - [ ] Structured logging throughout
   - [ ] Progress indicators
   - [ ] Performance metrics

3. **Testing and Documentation** (2 days)
   - [ ] Increase test coverage to 90%+
   - [ ] Integration tests for full pipeline
   - [ ] CLI documentation
   - [ ] Usage examples

**Success Criteria**:
- All CLI commands functional
- End-to-end pipeline working
- Test coverage > 90%
- Documentation complete

### Phase 3: Production Readiness 📅 PLANNED

**Objective**: Production-ready system with monitoring and advanced features

**Timeline**: 2-3 weeks

#### Features:

1. **Database Management**
   - Schema migrations
   - Backup and restore
   - IA synchronization
   - Performance optimization

2. **Configuration System**
   - Environment-based config
   - Secret management
   - Multi-environment support

3. **Monitoring and Observability**
   - Metrics collection
   - Health checks
   - Performance monitoring
   - Error tracking

4. **Advanced Features**
   - Multi-tribunal support framework
   - Batch processing optimization
   - Resume capability for long runs
   - Data validation layer

### Phase 4: Multi-Tribunal Expansion 📅 FUTURE

**Objective**: Support multiple tribunals with extensible framework

**Features**:
- Diario dataclass abstraction
- Tribunal adapter pattern
- Multi-tribunal collection
- Unified data model

---

## 🎯 Success Criteria

### Phase 1 (Foundation) ✅

- [x] All basic CLI commands working
- [x] Database operations functional
- [x] Test suite passing
- [x] 60%+ test coverage

### Phase 2 (Core Pipeline) 🔄

- [ ] Complete collect → analyze → score pipeline
- [ ] All CLI commands implemented
- [ ] 90%+ test coverage
- [ ] Production-ready error handling
- [ ] Comprehensive documentation

### Phase 3 (Production) 📅

- [ ] Database migrations working
- [ ] Configuration management complete
- [ ] Monitoring and observability
- [ ] Advanced features implemented
- [ ] Security review complete

### Phase 4 (Expansion) 📅

- [ ] Multi-tribunal support
- [ ] Extensible adapter pattern
- [ ] Scaling capabilities
- [ ] Performance optimization

---

## 📐 Technical Architecture

### Directory Structure

```
src/causaganha/
├── __init__.py
├── cli.py                 # CLI entry point (Typer)
├── config.py              # Configuration management
│
├── api/                   # External API clients
│   ├── __init__.py
│   ├── client.py          # PJe API client (httpx)
│   └── schemas.py         # API response schemas (Pydantic)
│
├── storage/               # Data persistence layer
│   ├── __init__.py
│   ├── connection.py      # DuckDB connection
│   ├── schema.py          # Database schema
│   ├── repository.py      # Repository pattern
│   └── queries.py         # Query helpers
│
├── domain/                # Business models
│   ├── __init__.py
│   └── models.py          # Domain entities
│
├── analysis/              # LLM analysis
│   ├── __init__.py
│   ├── analyzer.py        # Pydantic AI analyzer
│   └── models.py          # Analysis models
│
├── scoring/               # Rating system
│   ├── __init__.py
│   └── openskill.py       # OpenSkill implementation
│
├── pipeline/              # Orchestration
│   ├── __init__.py
│   ├── collect.py         # Collection pipeline
│   ├── analyze.py         # Analysis pipeline
│   ├── score.py           # Scoring pipeline
│   └── continuity.py      # Pipeline continuity
│
├── services/              # Application services
│   ├── __init__.py
│   └── document.py        # Document service
│
└── utils/                 # Utilities
    ├── __init__.py
    └── logging.py         # Logging configuration
```

### Data Flow

```
┌─────────────────┐
│  PJe API (TJRO) │
└────────┬────────┘
         │ collect
         ▼
┌─────────────────┐
│  DuckDB Storage │
└────────┬────────┘
         │ analyze
         ▼
┌─────────────────┐
│ Gemini LLM      │
└────────┬────────┘
         │ score
         ▼
┌─────────────────┐
│ OpenSkill       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  DuckDB Storage │
└─────────────────┘
```

### Key Design Decisions

1. **Repository Pattern**: Abstracts data access, enables testing
2. **Async-First**: All I/O operations are async
3. **Pydantic Validation**: Type-safe data models throughout
4. **Hexagonal Architecture**: Clear separation of concerns
5. **Dependency Injection**: Testable and flexible components

---

## 🚀 Getting Started

### Development Setup

```bash
# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv sync --dev
uv pip install -e .

# Initialize database
uv run causaganha db init

# Run tests
uv run pytest
```

### Basic Usage

```bash
# Collect intimations
uv run causaganha collect --start-date 2024-01-01 --end-date 2024-01-31

# Analyze decisions
uv run causaganha analyze --limit 10

# Check database status
uv run causaganha db status
```

---

## 📝 Development Guidelines

### Code Style

- Follow PEP 8
- Use type hints throughout
- Async functions for I/O operations
- Pydantic models for data validation
- Comprehensive docstrings

### Testing

- Write tests before implementation (TDD)
- Minimum 80% coverage
- Unit tests for logic
- Integration tests for workflows
- Mock external dependencies

### Git Workflow

- Feature branches: `feat/feature-name`
- Bug fixes: `fix/bug-description`
- Clear commit messages
- PR for all changes

### Documentation

- Update CLAUDE.md for major changes
- Document all CLI commands
- API documentation with examples
- Keep this plan updated

---

## 🐛 Known Issues and Limitations

### Current Limitations

1. **Archive Command**: Not yet implemented
2. **Score Command**: Missing from CLI
3. **Pipeline Orchestration**: No unified command
4. **Error Recovery**: Basic error handling only
5. **Multi-Tribunal**: Only TJRO supported

### Technical Debt

1. **Document Service**: Incomplete implementation (31% coverage)
2. **CLI Coverage**: Only 66% coverage
3. **Error Messages**: Need more user-friendly messages
4. **Configuration**: Hardcoded values need externalization

---

## 📚 References

- [MASTERPLAN.md](./plans/MASTERPLAN.md) - Overall project coordination
- [System Integration Resolution](./plans/system-integration-resolution.md) - Integration plan
- [CLAUDE.md](../CLAUDE.md) - Development guidelines

---

## 📊 Progress Tracking

**Overall Progress**: 60% Complete

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Foundation | ✅ Complete | 100% |
| Phase 2: Core Pipeline | 🔄 In Progress | 40% |
| Phase 3: Production | 📅 Planned | 0% |
| Phase 4: Expansion | 📅 Future | 0% |

**Test Status**: 33 tests passing, 85% coverage

**Last Commit**: e0c5e0c - Merge pull request #126

---

**Status**: 🔄 **ACTIVE DEVELOPMENT** - Phase 2 in progress, implementing core pipeline commands and orchestration.

**Priority**: 🔥 **HIGH** - Foundation for all future features and multi-tribunal expansion.

**Compatibility**: ✅ **ALIGNED** - Fully compatible with MASTERPLAN phases and timeline.
