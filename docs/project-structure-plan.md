# Project Structure Modernization Plan

**Status**: Planning Phase  
**Priority**: P1 (Enhancement)  
**Estimated Effort**: 1-2 days  
**Target**: Migrate to modern Python project structure following best practices

## Overview

This plan restructures CausaGanha to follow modern Python packaging standards, improve developer experience, and prepare for potential PyPI distribution. The current structure mixes source code with data and configuration, making it harder to maintain and package.

## Current Structure Analysis

### 🔴 **Current Issues**
```
causa_ganha/
├── causaganha/               # Source code mixed with data
│   ├── core/                # Business logic
│   ├── tests/               # Tests scattered
│   └── data/                # Data mixed with source
├── data/                    # Duplicate data directories
├── docs/                    # Documentation (good)
├── pipeline/                # Workflow scripts separate
├── migrations/              # Database migrations separate
├── .github/                 # CI/CD (good)
└── config files             # Root level config
```

### ⚠️ **Problems Identified**
- **Non-standard layout**: Doesn't follow Python packaging conventions
- **Mixed concerns**: Source code and data in same directory
- **Import complexity**: Awkward import paths and module resolution
- **Testing issues**: Tests not easily discoverable by pytest
- **Distribution problems**: Cannot easily package for PyPI
- **Developer confusion**: Non-intuitive project navigation

## Proposed Structure

### ✅ **Simplified Modern Layout**
```
causa_ganha/
├── src/
│   └── causaganha/              # Main package
│       ├── __init__.py
│       ├── cli.py               # Command-line interface (single file)
│       ├── database.py          # Database operations
│       ├── extractor.py         # PDF extraction with Gemini
│       ├── pipeline.py          # Pipeline orchestration
│       ├── downloader.py        # PDF downloading
│       ├── trueskill_rating.py  # TrueSkill calculations
│       ├── r2_storage.py        # Cloudflare R2 operations
│       ├── r2_queries.py        # R2 analytics queries
│       ├── migration_runner.py  # Database migrations
│       ├── utils.py             # Utility functions
│       └── config.py            # Configuration management
├── tests/
│   ├── conftest.py             # Pytest configuration
│   ├── test_database.py
│   ├── test_extractor.py
│   ├── test_pipeline.py
│   └── fixtures/               # Test data
│       └── sample_data/
├── scripts/
│   ├── collect_and_archive.py  # Internet Archive workflows
│   └── setup_dev.py           # Development setup
├── data/                       # Data storage (mostly git-ignored)
│   └── samples/               # Sample data for testing
├── migrations/                 # Database migrations
│   └── 001_init.sql
├── docs/                       # Documentation
├── .github/                    # GitHub Actions
├── pyproject.toml             # Modern Python project config
├── config.toml.example        # Configuration template
├── README.md
└── .env.example
```

## Migration Plan

### **Phase 1: Prepare New Structure**

#### 1.1 Create New Directory Structure
```bash
# Create simplified src-based layout
mkdir -p src/causaganha
mkdir -p tests/fixtures/sample_data
mkdir -p scripts
mkdir -p data/samples
touch src/causaganha/__init__.py
```

#### 1.2 Update Project Configuration
```toml
# pyproject.toml (NEW)
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "causaganha"
version = "1.0.0"
description = "Automated judicial decision analysis using TrueSkill rating system"
authors = [{name = "CausaGanha Team"}]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "duckdb>=1.0.0",
    "pandas>=2.0.0",
    "trueskill>=0.4.5",
    # ... other dependencies
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "black>=23.0.0",
]

[project.scripts]
causaganha = "causaganha.cli.main:main"

[tool.setuptools.packages.find]
where = ["src"]
```

### **Phase 2: Move Source Code**

#### 2.1 Migrate Core Modules
```bash
# Move core business logic (flat structure)
mv causaganha/core/* src/causaganha/
# Move pipeline script
mv pipeline/collect_and_archive.py scripts/
# Move tests
mv causaganha/tests/* tests/
```

#### 2.2 Simplify CLI Structure
```python
# src/causaganha/cli.py
"""Command-line interface for CausaGanha."""
import argparse
from causaganha.pipeline import main as pipeline_main
from causaganha.database import CausaGanhaDB
from causaganha.migration_runner import run_migrations

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="CausaGanha - Judicial Decision Analysis")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Pipeline commands (keep existing interface)
    pipeline_parser = subparsers.add_parser('pipeline', help='Run pipeline operations')
    pipeline_parser.add_argument('action', choices=['collect', 'extract', 'update', 'run'])
    pipeline_parser.add_argument('--date', help='Date to process')
    pipeline_parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    
    # Database commands
    db_parser = subparsers.add_parser('db', help='Database operations')
    db_parser.add_argument('action', choices=['migrate', 'status', 'backup'])
    
    args = parser.parse_args()
    
    if args.command == 'pipeline':
        # Delegate to existing pipeline main
        pipeline_main()
    elif args.command == 'db':
        handle_db_command(args)
    else:
        parser.print_help()
```

#### 2.3 Modernize Imports
```python
# Before (current)
from causaganha.core.database import CausaGanhaDB

# After (new structure)
from causaganha.core.database import CausaGanhaDB
```

### **Phase 3: Update Tests**

#### 3.1 Consolidate Test Structure
```bash
# Move all tests to unified location (already done in Phase 2)
# Simple flat test structure - no unit/integration separation needed yet
```

#### 3.2 Update Test Configuration
```python
# tests/conftest.py
"""Pytest configuration for CausaGanha tests."""
import pytest
from pathlib import Path
import tempfile
import sys

# Add src to Python path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

@pytest.fixture
def temp_db():
    """Provide temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False) as tmp:
        yield Path(tmp.name)
        Path(tmp.name).unlink(missing_ok=True)

@pytest.fixture  
def sample_pdf():
    """Provide sample PDF for testing."""
    return Path(__file__).parent / "fixtures" / "sample_pdfs" / "test.pdf"
```

### **Phase 4: Update Configuration**

#### 4.1 Simplify Configuration Management
```python
# src/causaganha/config.py
"""Simple configuration management for CausaGanha."""
import toml
from pathlib import Path
from typing import Dict, Any

DEFAULT_CONFIG = {
    "database": {"path": "data/causaganha.duckdb"},
    "trueskill": {"mu": 25.0, "sigma": 8.333},
    "logging": {"level": "INFO"}
}

def load_config(config_path: Path = None) -> Dict[str, Any]:
    """Load configuration from file or return defaults."""
    if config_path is None:
        config_path = Path("config.toml")
    
    if config_path.exists():
        return toml.load(config_path)
    return DEFAULT_CONFIG.copy()
```

#### 4.2 Simple Configuration Template
```toml
# config.toml.example
[database]
path = "data/causaganha.duckdb"

[trueskill]
mu = 25.0
sigma = 8.333
beta = 4.167

[logging]
level = "INFO"
```

### **Phase 5: Update Workflows**

#### 5.1 Update GitHub Actions
```yaml
# .github/workflows/test.yml (updated)
- name: Install dependencies
  run: |
    uv sync --dev
    uv pip install -e .  # Install package in development mode

- name: Run tests
  run: |
    uv run pytest tests/ --cov=src/causaganha --cov-report=xml
```

#### 5.2 Update Scripts
```python
# scripts/setup_dev.py
"""Development environment setup script."""
import subprocess
import sys
from pathlib import Path

def setup_development():
    """Set up development environment."""
    print("Setting up CausaGanha development environment...")
    
    # Install in development mode
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", ".[dev]"])
    
    # Create data directories
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    # Copy example config
    if not Path("config.toml").exists():
        subprocess.run(["cp", "config/config.example.toml", "config.toml"])
    
    print("✅ Development environment ready!")

if __name__ == "__main__":
    setup_development()
```

## Benefits of New Structure

### **🚀 Developer Experience**
- **Standard layout**: Familiar to Python developers
- **Clear separation**: Source, tests, docs, and data properly organized
- **Easy imports**: Intuitive module resolution
- **IDE support**: Better code completion and navigation
- **Type checking**: Easier mypy and pyright integration

### **📦 Packaging & Distribution**
- **PyPI ready**: Can easily publish to Python Package Index
- **Editable installs**: `pip install -e .` for development
- **Dependency management**: Clear project dependencies
- **Version management**: Centralized in pyproject.toml
- **Entry points**: Command-line tools automatically available

### **🧪 Testing & Quality**
- **Unified tests**: All tests in predictable location
- **Coverage reporting**: Easy coverage measurement
- **Fixture management**: Centralized test data
- **CI/CD compatibility**: Standard structure works with all tools
- **Test discovery**: Pytest finds all tests automatically

### **🔧 Maintenance & Operations**
- **Configuration management**: Environment-specific configs
- **Logging consistency**: Centralized logging configuration
- **Script organization**: Utility scripts in dedicated directory
- **Documentation structure**: Organized docs for different audiences
- **Migration tracking**: Clear database migration management

## Migration Steps

### **Week 1: Structure Preparation**
- [ ] Create new directory structure
- [ ] Set up pyproject.toml configuration
- [ ] Create CLI entry points
- [ ] Prepare configuration management system

### **Week 2: Code Migration**
- [ ] Move core modules to src/causaganha/core/
- [ ] Update all import statements
- [ ] Migrate tests to unified tests/ directory
- [ ] Update test configuration and fixtures

### **Week 3: Integration & Testing**
- [ ] Update GitHub Actions workflows
- [ ] Test all CLI commands with new structure
- [ ] Verify all imports and module resolution
- [ ] Run full test suite and fix any issues

### **Week 4: Documentation & Cleanup**
- [ ] Update all documentation with new structure
- [ ] Create development setup scripts
- [ ] Clean up old directory structure
- [ ] Update CLAUDE.md with new architecture

## Risk Assessment

### **🔄 Migration Risks**
- **Import breakage**: Existing code may break during migration
- **Test failures**: Tests may need significant updates
- **CI/CD disruption**: Workflows may need debugging
- **Developer confusion**: Team needs to learn new structure

### **⚡ Mitigation Strategies**
- **Gradual migration**: Move modules incrementally
- **Comprehensive testing**: Verify each step thoroughly
- **Documentation**: Clear migration guides for developers
- **Rollback plan**: Keep old structure until verification complete

## Success Metrics

### **📈 Technical Metrics**
- **Test coverage**: Maintain or improve current coverage
- **Import resolution**: All imports work correctly
- **CI/CD success**: All workflows pass after migration
- **Performance**: No degradation in execution speed

### **👥 Developer Metrics**
- **Setup time**: Faster development environment setup
- **Code navigation**: Improved IDE experience
- **Contribution ease**: Easier for new developers to contribute
- **Maintenance efficiency**: Faster debugging and maintenance

## Future Enhancements

### **🔮 Post-Migration Opportunities**
- **PyPI distribution**: Publish causaganha package
- **Plugin architecture**: Support for external extensions
- **API server**: Web API using FastAPI
- **Docker support**: Containerized deployment
- **Package splitting**: Separate core, cli, and web packages

---

**Next Steps**: Review with team, validate approach, and begin Phase 1 implementation.