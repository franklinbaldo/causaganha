# CLAUDE.md

![Alpha](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)
![Breaking Changes](https://img.shields.io/badge/breaking_changes-expected-red?style=for-the-badge)
![No Backwards Compatibility](https://img.shields.io/badge/backwards_compatibility-none-critical?style=for-the-badge)

> ⚠️ **ALPHA SOFTWARE**: This project is in active development with frequent breaking changes. APIs, database schemas, and core functionality may change without notice or backwards compatibility. Use at your own risk in production environments.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CausaGanha is an automated judicial decision analysis platform that applies the OpenSkill rating system to evaluate lawyer performance in legal proceedings. It extracts, analyzes, and scores judicial decisions from Brazilian tribunals using Google's Gemini LLM with local DuckDB storage and Internet Archive for PDF archiving.

## Development Setup

This project uses **uv** for dependency management and follows modern Python packaging standards:

```bash
# Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uv sync --dev
uv pip install -e .  # Install package in development mode
```

Environment variables (copy `.env.example` to `.env`):

- `GEMINI_API_KEY`: Required for PDF content extraction
- `IA_ACCESS_KEY`: Required for Internet Archive uploads and database sync
- `IA_SECRET_KEY`: Required for Internet Archive uploads and database sync

## Development Flow

CausaGanha follows a **plan-first development approach** to ensure thoughtful feature design and implementation:

### 📋 **Phase 1: Planning**

1. **Create Plan Document**: New features must start as a plan in `/docs/plans/feature-name.md`
2. **Problem Context**: The plan must clearly explain:
   - What problem it's trying to solve
   - Why this solution is needed
   - Current limitations or pain points
3. **Actionable Solution**: The plan must provide:
   - Concrete implementation steps
   - Technical approach and architecture decisions
   - Expected outcomes and success criteria
   - Potential risks and mitigations

### 🔍 **Phase 2: Review & Approval**

1. **Plan Review**: The plan document is reviewed for:
   - Technical feasibility
   - Alignment with project goals
   - Implementation clarity
   - Resource requirements
2. **Merge to Main**: Once approved, the plan is merged to `main` branch
3. **Implementation Ready**: Plan serves as the implementation specification

### 🚀 **Phase 3: Implementation**

1. **Feature Branch**: Implementation happens in separate feature branches
2. **Incremental Development**: Features are built according to the approved plan
3. **Testing & Validation**: Implementation includes comprehensive tests
4. **Code Review**: Standard pull request review process

### 📚 **Phase 4: Documentation**

1. **Feature Complete**: Once the plan is fully implemented and tested
2. **Documentation Conversion**: The original plan document is transformed into:
   - User documentation explaining how to use the feature
   - Technical documentation explaining the implementation
   - Examples and usage patterns
3. **Move Documentation**: The updated documentation is moved:
   - **Major features**: From `/docs/plans/` to `/docs/implemented/`
   - **Core system docs**: From `/docs/plans/` directly to `/docs/` (for fundamental features)
   - **Archive original plan**: Keep implementation history for reference

### 📁 **Directory Structure**

```
docs/
├── plans/                      # 📋 Future features (planning phase)
│   ├── MASTERPLAN.md           # 🎯 LIVE COORDINATION DOCUMENT
│   ├── diario-class.md         # Plan: Diario dataclass system
│   ├── dtb.md                  # Plan: dbt-duckdb migration
│   ├── fix-database-integration-issues.md  # Plan: Database integration fixes
│   ├── multi_tribunal_collection.md        # Plan: Multi-tribunal support
│   ├── prompt_versioning_strategy.md       # Plan: LLM prompt versioning
│   └── refactor_archive_command.md         # Plan: Archive command refactor
├── implemented/                # 📚 Completed features (documentation)
│   └── (empty - features will move here when complete)
├── cli_design.md              # Current: CLI architecture and commands
├── faq.md                     # Current: Frequently asked questions
├── ia_discovery_guide.md      # Current: Internet Archive discovery tools
└── openskill.md               # Current: OpenSkill rating system
```

### ✅ **Planning Template**

When creating a new plan, use this structure:

```markdown
# Feature Name

## Problem Statement

- What problem does this solve?
- Why is this important?
- Current limitations

## Proposed Solution

- High-level approach
- Technical architecture
- Implementation steps

## Success Criteria

- How do we know it's working?
- What are the expected outcomes?

## Implementation Plan

1. Step 1: Description
2. Step 2: Description
3. Step 3: Description

## Risks & Mitigations

- Risk 1: Mitigation strategy
- Risk 2: Mitigation strategy
```

This approach ensures all new features are well-planned, reviewed, and properly documented throughout their lifecycle.

## 🎯 **MASTERPLAN Coordination**

CausaGanha uses a **living MASTERPLAN document** to coordinate all implementation efforts:

### **📍 MASTERPLAN Location**

- **Primary Document**: `/docs/plans/MASTERPLAN.md`
- **Status**: Live coordination document (updated with each implementation phase)
- **Purpose**: Ensures compatibility, proper sequencing, and resource allocation across all plans

### **🔄 MASTERPLAN Workflow**

1. **Before Creating New Plans**: Check MASTERPLAN for existing priorities and phases
2. **After Creating Plans**: Update MASTERPLAN to include new plan and assess compatibility
3. **During Implementation**: Update progress tracking and phase completion in MASTERPLAN
4. **Resource Conflicts**: Use MASTERPLAN to coordinate developer allocation and timing

### **⚠️ Alpha Development Guidelines**

- **MASTERPLAN drives implementation order**: Follow phase priorities to avoid conflicts
- **Breaking changes coordination**: Use MASTERPLAN to batch compatible breaking changes
- **Dependencies management**: MASTERPLAN critical path prevents implementation deadlocks
- **Quality gates**: Phase completion requirements ensure system stability

### **📊 MASTERPLAN Maintenance**

- **Weekly updates**: Implementation progress and phase completion tracking
- **Plan additions**: New plans must be integrated into existing phase structure
- **Conflict resolution**: Incompatible plans require MASTERPLAN revision and replanning
- **Resource planning**: Developer allocation and timeline coordination

**The MASTERPLAN is the single source of truth for coordinated development in the alpha phase.**

## 🤖 **Agent Registry System**

CausaGanha implements a **parallel development system** using an agent registry for scalable, conflict-free collaboration:

### **📁 Agent Registry Structure**

```
.agents/
├── README.md              # Central coordination and communication guidelines
├── testing-docs.md             # Testing & Documentation specialist
├── quality-docs.md             # Quality & Documentation specialist
├── infrastructure-devex.md             # Infrastructure & DevEx specialist
└── monitoring-integration.md            # Monitoring & Integration specialist
```

### **🎯 Agent Sprint System**

- **Sprint-based delivery**: Each agent works on 5 tasks per sprint (2-3 week cycles)
- **File boundary enforcement**: Agents have exclusive write access to specific directories/files
- **Zero-conflict development**: Strict file boundaries prevent merge conflicts
- **Single PR delivery**: All agent work delivered in one comprehensive PR at sprint end

### **📋 Agent Communication Flow**

1. **Task Assignment**: Agents receive tasks in their individual `.md` cards
2. **Autonomous Work**: Agents work independently within their file boundaries
3. **Progress Tracking**: Real-time updates in agent cards with scratchpad notes
4. **Strategic Input**: Agents can ask questions about future tasks, project architecture, and process improvements
5. **Feedback Loop**: Responses provided directly in agent cards using Wikipedia-style signatures

### **🔧 Communication Guidelines**

Agents can use their cards to:

- ✅ **Ask about**: Next sprint planning, architecture suggestions, process improvements, collaboration opportunities
- ✅ **Update**: Progress tracking, implementation notes, technical decisions
- ❌ **Avoid asking**: Current deliverable implementation details (work autonomously)

### **🎪 File Zone Management**

Each agent has exclusive access to specific areas:

- **testing-docs**: `tests/test_extractor.py`, `tests/test_ia_discovery.py`, `tests/benchmarks/`, `docs/api/`, `docs/tutorials/`
- **quality-docs**: `tests/mock_data/`, `tests/test_error_simulation.py`, `docs/diagrams/`, `docs/faq.md`, `docs/examples/`
- **infrastructure-devex**: `ruff.toml`, `.pre-commit-config.yaml`, `.github/workflows/`, `.vscode/`, `Docker*`, `scripts/`
- **monitoring-integration**: `src/` (type hints only), `src/utils/logging_config.py`, `scripts/{dev,db,env}/`, `.env.example`

### **🚀 Integration Benefits**

- **Parallel Development**: Multiple improvement streams without blocking main development
- **Quality Assurance**: All agent work includes comprehensive tests and documentation
- **Scalable Process**: Agent registry can grow with project needs
- **Professional Standards**: Maintains high code quality across all contributions

**See `.agents/README.md` for detailed communication guidelines and current sprint status.**

## Core Commands

### Modern CLI (Primary Interface)

CausaGanha now provides a modern, user-friendly CLI for judicial document processing:

```bash
# Queue URLs from CSV file
uv run --env-file .env causaganha queue --from-csv diarios.csv

# Download and archive to Internet Archive
uv run --env-file .env causaganha archive --limit 10

# Extract information using Gemini LLM
uv run --env-file .env causaganha analyze --limit 5

# Calculate OpenSkill ratings
uv run --env-file .env causaganha score

# Run full pipeline in one command
uv run --env-file .env causaganha pipeline --from-csv diarios.csv

# Monitor progress and statistics
uv run --env-file .env causaganha stats

# Database management
uv run --env-file .env causaganha db status
uv run --env-file .env causaganha db migrate
uv run --env-file .env causaganha db backup
```

### Legacy Async Pipeline (Advanced Users)

For advanced users, the original async pipeline is still available:

```bash
# Legacy async pipeline commands
uv run --env-file .env python src/async_diario_pipeline.py --max-items 5
```

### Database Backup and Export

Local DuckDB database with optional Internet Archive backup:

```bash
# Export database to Internet Archive for backup
uv run --env-file .env causaganha db export

# Check database status
uv run --env-file .env causaganha db status

# Create local backup
uv run --env-file .env causaganha db backup
```

### Internet Archive Discovery

Tools for discovering and analyzing uploaded diarios:

```bash
# List uploaded diarios for specific year
uv run --env-file .env python src/ia_discovery.py --year 2025

# Coverage analysis (what's missing vs expected)
uv run --env-file .env python src/ia_discovery.py --coverage-report

# Export complete inventory
uv run --env-file .env python src/ia_discovery.py --export inventory.json

# Check specific item exists
uv run --env-file .env python src/ia_discovery.py --check-identifier tjro-diario-2025-06-26
```

### Testing & Quality

```bash
# Run all tests (required before commits)
uv run pytest -q

# Run specific test file
uv run pytest tests/test_downloader.py -v

# Code formatting and linting
uv run ruff format
uv run ruff check
uv run ruff check --fix  # Auto-fix issues
```

## Architecture Overview

### Local Database with Archive Backup

CausaGanha uses a **local DuckDB database** with optional Internet Archive backup for data persistence:

- **Local Storage**: Primary DuckDB database file (`data/causaganha.duckdb`)
- **Cross-Platform**: Works from any environment (Windows, Linux, macOS)
- **Backup System**: Optional export to Internet Archive for data preservation
- **Simple Management**: Direct file operations without complex synchronization

### Four-Stage Data Lifecycle Pipeline

**Modern CLI Interface**: Primary user interface with `causaganha` command providing intuitive access to all pipeline stages.

**Pipeline Stages**:

1. **Queue** (`causaganha queue`): Add judicial documents to processing queue
   - **Flexible Input**: URLs or CSV files with automatic tribunal detection
   - **Domain Validation**: Only .jus.br domains accepted for security
   - **Smart Detection**: Auto-extract date and metadata from URLs

2. **Archive** (`causaganha archive`):
   - **Concurrent Processing**: Downloads multiple PDFs simultaneously from TJRO
   - **Internet Archive Upload**: Direct upload to IA with metadata preservation
   - **Original Filename Preservation**: Maintains authentic TJRO naming (e.g., `20250626614-NR115.pdf`)
   - **Progress Tracking**: Resume capability with persistent progress files
   - **Rate Limiting**: Respectful to TJRO servers (3 concurrent downloads max)

3. **Analyze** (`causaganha analyze`):
   - **Gemini LLM Processing**: Uses Google's Gemini 2.5 Flash for content analysis
   - **Chunked Processing**: 25-page segments with 1-page overlap for context
   - **Temporary Files**: All processing artifacts in temp directories (no data pollution)
   - **Enhanced Data**: Extracts process numbers, parties, lawyers with OAB, outcomes
   - **JSON Output**: Structured data with automatic validation

4. **Score** (`causaganha score`):
   - **OpenSkill Algorithm**: Advanced rating system for skill assessment
   - **Team Formation**: Lawyers grouped by case sides (polo ativo/passivo)
   - **Database Storage**: All data unified in DuckDB format
   - **Shared Updates**: Changes automatically synced to IA for global access

### Key Modules

#### Modern CLI Interface

- **`cli.py`**: **NEW** - Modern Typer-based CLI with 4-stage pipeline
  - Queue, Archive, Analyze, Score commands with rich progress display
  - Database management (migrate, status, sync, backup, reset)
  - Pipeline orchestration with resume capability and error handling
  - .jus.br domain validation and smart metadata extraction

#### Core Processing

- **`async_diario_pipeline.py`**: **NEW** - Main async pipeline with concurrent processing
- **`ia_discovery.py`**: **NEW** - Tools for discovering uploaded content in IA
- **`extractor.py`**: Gemini-powered content extraction with temp file handling
- **`openskill_rating.py`**: OpenSkill rating calculations and environment setup

#### Data Management

- **`database.py`**: **NEW** - Unified DuckDB data layer for all system storage
- **`diario_processor.py`**: **NEW** - Convert raw TJRO data to pipeline-ready format
- **`utils.py`**: Lawyer name normalization and decision validation utilities
- **`config.py`**: Configuration management with TOML support

#### Legacy Integration

- **`pipeline.py`**: Legacy orchestrator (use async_diario_pipeline.py instead)
- **`downloader.py`**: Individual PDF downloads (integrated into async pipeline)

### Complete Data Architecture

The system implements a **simplified local-first storage strategy** for optimal performance and simplicity:

#### Primary Storage: Local DuckDB

- **`data/causaganha.duckdb`**: Main database file with unified schema
- **Core Tables**: ratings, partidas, decisoes, pdf_metadata, json_files
- **High Performance**: Direct local access for development and processing

#### Archive Storage: Internet Archive (PDF Storage & Backup)

- **PDF Archive**: All diarios permanently stored with proper metadata
- **Database Backup**: Optional export of database for data preservation
- **Public Access**: Complete transparency with research-friendly URLs
- **Zero Cost**: Free permanent storage with global CDN
- **Simple Operations**: Direct file upload/download without complex synchronization

### Data Flow

```
TJRO Website → Async Download → Internet Archive → Gemini Analysis → OpenSkill Updates → Local Database
                     ↓              ↓                   ↓                  ↓              ↓
                Original Names   Public Archive      JSON Extraction    Rating Updates   DuckDB Storage
                     ↓              ↓                   ↓                  ↓              ↓
               Progress Tracking  Permanent Storage   Temp Processing   Local DuckDB    Optional Backup
```

### File Organization

- **`src/`**: **Main modules** - Flatter Python src-layout structure
  - `async_diario_pipeline.py`: **NEW** - Primary async processing pipeline
  - `ia_discovery.py`: **NEW** - IA content discovery and analysis
  - `diario_processor.py`: **NEW** - Data format conversion utilities
  - `extractor.py`: Gemini-powered content extraction
  - `database.py`: DuckDB data layer operations
  - All other core modules directly in src/
- **`tests/`**: **Unified test suite** - All tests in one location
  - Comprehensive unit tests with pytest configuration
  - Mock-based tests for external API calls
  - Coverage reporting for src/ modules
- **`data/`**: **Unified data directory**
  - `data/causaganha.duckdb`: **Main database** - synced with IA
  - `data/diarios_pipeline_ready.json`: **NEW** - 5,058 diarios ready for processing
  - `data/todos_diarios_tjro.json`: **NEW** - Complete TJRO diario list (2004-2025)
  - `data/diarios_2025_only.json`: **NEW** - Filtered current year for testing
  - `data/diarios/`: Downloaded PDFs with original TJRO filenames
- **`.github/workflows/`**: **Automated CI/CD** with **4 modern workflows**
  - `pipeline.yml`: **NEW** - Daily async pipeline with database sync
  - `bulk-processing.yml`: **NEW** - Large-scale processing with multiple modes
  - `database-archive.yml`: Weekly/monthly database snapshots to IA
  - `test.yml`: Quality assurance with comprehensive testing

## Testing Requirements

Per `AGENTS.md`: Always run `uv run pytest -q` before committing changes. The test suite includes:

- Mock-based tests for external API calls (Gemini, TJRO website, IA)
- OpenSkill calculation validation with known scenarios
- Async pipeline functionality with proper error handling
- Database synchronization and locking mechanisms
- JSON parsing and validation logic

## GitHub Actions Integration

**Four automated workflows** handle the complete data lifecycle with local database and backup support:

#### 1. Daily Async Pipeline (`pipeline.yml`)

- **Daily at 03:15 UTC** - Processes latest 5 diarios automatically
- **Manual dispatch** - Flexible date ranges, item limits, force reprocessing
- **Database backup** - Optional export to Internet Archive after processing
- **Comprehensive reporting** - Statistics, IA discovery, progress tracking

#### 2. Bulk Processing (`bulk-processing.yml`) ⭐ **NEW**

- **On-demand processing** - Handle large-scale operations (up to all 5,058 diarios)
- **Multiple modes**: year_2025, year_2024, last_100, last_500, all_diarios, custom_range
- **Concurrency tuning** - Configurable download/upload limits
- **6-hour timeout** - Handles massive processing jobs
- **Database backup** - Optional export to Internet Archive after processing

#### 3. Database Archive (`database-archive.yml`)

- **Weekly on Sunday at 04:00 UTC** - Database snapshots to IA
- **Monthly archives** - First Sunday of each month (permanent retention)
- **Public research** - Makes complete OpenSkill datasets publicly available
- **Deduplication** - Skips upload if archive already exists

#### 4. Quality Assurance (`test.yml`)

- **On PR/Push** - Comprehensive testing with all core components
- **Auto-formatting** - Automatic ruff formatting and linting
- **Coverage reporting** - Ensures code quality standards

**Required repository secrets:**

- `GEMINI_API_KEY` (required for PDF extraction)
- `IA_ACCESS_KEY` (required for Internet Archive operations)
- `IA_SECRET_KEY` (required for Internet Archive operations)

## External Dependencies

- **Google Gemini API**: Core LLM for PDF content extraction
  - **Model**: `gemini-2.5-flash-lite-preview-06-17`
  - **Rate limits**: 15 RPM with automatic backoff
  - **Features**: Chunked analysis with overlap for context continuity
- **PyMuPDF (fitz)**: Local PDF text extraction library
- **TJRO Website**: Source of judicial PDFs via direct download URLs
- **Internet Archive**:
  - **PDF storage**: All PDFs permanently archived
  - **Database backup**: Optional export for data preservation
  - **Public access**: Permanent URLs for transparency
  - **CLI tools**: Uses `ia` command-line tool for operations
- **DuckDB**: High-performance embedded database for all data storage
- **aiohttp**: Async HTTP operations for concurrent processing

## System Overview & Achievements

### 🎯 Alpha Local-First Solution

CausaGanha has evolved into an **alpha-stage, local-first judicial analysis platform** with:

#### ✅ **Simplified Local Database Architecture**

- **Local-First Storage**: Primary DuckDB database for immediate access and processing
- **Simple Backup System**: Optional export to Internet Archive for data preservation
- **Direct File Operations**: No complex synchronization or locking mechanisms
- **Internet Archive for PDFs**: Zero-cost, permanent, globally accessible PDF storage

#### ✅ **Async Processing Pipeline**

- **Concurrent Operations**: Process multiple diarios simultaneously
- **Original Filename Preservation**: Maintains authentic TJRO naming conventions
- **Progress Tracking**: Resume capability for interrupted processing
- **Temporary File Handling**: Clean separation of processing vs permanent data

#### ✅ **Comprehensive Discovery System**

- **Coverage Analysis**: Track what's uploaded vs what should exist
- **Inventory Management**: Export complete catalogs of processed content
- **Public Transparency**: All judicial records publicly accessible via IA

#### ✅ **Advanced GitHub Actions**

- **4 specialized workflows** with local database and backup integration
- **Bulk processing** capabilities for massive datasets (5,058+ diarios)
- **Simple data management** without complex synchronization requirements
- **Comprehensive reporting** with statistics and discovery tools

#### ✅ **Alpha Quality Features**

- **60+ unit tests** with comprehensive mocking of external APIs
- **Database backup** tested with real IA integration
- **Simple file operations** eliminate complex synchronization issues
- **Error recovery** with exponential backoff and retry logic
- **⚠️ Breaking changes expected**: Core APIs and data structures may change

### 🚀 **Operational Excellence**

The system demonstrates **enterprise-grade local-first architecture** with:

- **High-performance local access**: Direct DuckDB operations for optimal speed
- **Simple data management**: No complex synchronization or locking requirements
- **Automatic scaling**: Handles datasets from single items to 21+ years of records
- **Cost optimization**: Leverages free IA storage for massive PDF datasets
- **Global accessibility**: Public transparency through permanent IA URLs

### 🎖️ **Technical Innovation**

- **Local-first database**: High-performance DuckDB with optional Internet Archive backup
- **Async judicial processing**: Concurrent analysis of legal documents at scale
- **Original filename preservation**: Maintains archival authenticity
- **Simplified data management**: Direct file operations without complex synchronization

The system processes judicial records from 2004-2025 (21+ years) with complete automation, local-first storage, and public transparency.

## ⚠️ Alpha Status Warning

**CausaGanha is ALPHA software** with the following implications:

- **Breaking Changes**: Core APIs, CLI commands, and database schemas may change without notice
- **No Backwards Compatibility**: Updates may require complete data migration or reinstallation
- **Experimental Features**: New functionality may be added, modified, or removed rapidly
- **API Instability**: Function signatures, return types, and behavior may change
- **Data Format Changes**: Database schema and file formats may evolve incompatibly
- **Configuration Changes**: Settings and environment variables may be restructured

**Use in production at your own risk.** Consider this software experimental and expect to adapt to breaking changes.

## Claude Code Instructions

When working with this codebase, follow the **plan-first development approach**:

### 🎯 **For New Features**

1. **Check MASTERPLAN first**: Always consult `/docs/plans/MASTERPLAN.md` to understand current implementation phases and priorities
2. **Always start with planning**: Before implementing any new feature, create a comprehensive plan in `/docs/plans/`
3. **Use the planning template**: Follow the structured format with problem statement, solution, implementation steps, and risks
4. **Update MASTERPLAN**: Add new plans to MASTERPLAN.md and assess compatibility with existing plans
5. **Get plan approval**: Plans should be reviewed and merged before implementation begins
6. **Reference existing plans**: Check `/docs/plans/` for similar features or architectural patterns

### 📋 **When Creating Plans**

- **Be specific**: Include concrete implementation steps, not just high-level ideas
- **Consider architecture**: Explain how the feature fits into the existing system
- **Identify risks**: Think about potential issues and mitigation strategies
- **Define success**: Clear criteria for when the feature is considered complete

### 🚀 **During Implementation**

- **Follow the plan**: Implement according to the approved specification
- **Create feature branch**: Use separate branches for each feature development
- **Test thoroughly**: Include comprehensive tests for new functionality
- **Update documentation**: Transform the plan into user/technical documentation when complete

### 📚 **After Implementation**

- **Convert plan to docs**: Transform the plan into proper documentation
- **Move to appropriate location**:
  - Major features → `/docs/implemented/`
  - Core system features → `/docs/`
- **Update references**: Ensure all documentation links are updated

### 🔍 **Plan Review Checklist**

- [ ] Problem clearly defined and justified
- [ ] Solution approach is technically sound
- [ ] Implementation steps are actionable
- [ ] Success criteria are measurable
- [ ] Risks are identified with mitigations
- [ ] Fits with existing architecture
- [ ] Considers alpha status and breaking changes

This approach ensures thoughtful development and maintains high-quality documentation throughout the feature lifecycle.

### 🤖 **Agent Registry Integration with Planning**

The agent registry system complements the plan-first approach:

- **Strategic Planning**: MASTERPLAN and plans focus on high-level architecture and feature design
- **Tactical Execution**: Agent registry handles quality improvements, testing, documentation, and tooling
- **Parallel Development**: Main development follows critical path while agents enhance system quality
- **Communication Flow**: Agents can suggest improvements to plans and architecture through their cards
- **Resource Efficiency**: Reduces bottlenecks by distributing non-critical-path work across specialized agents

---

**Status: 🔶 ALPHA LOCAL-FIRST** - Simplified local database architecture (2025-07-09): local-first storage, optional backup, async processing, and comprehensive automation. Alpha-stage local-first judicial analysis platform with breaking changes expected.
