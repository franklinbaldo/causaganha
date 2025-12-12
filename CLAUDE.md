# CLAUDE.md

![Alpha](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)

> ⚠️ **ALPHA SOFTWARE**: Active V2 Development.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚀 V2 Construction Mode

**CausaGanha is currently building V2**. V1 has been archived to `legacy_archive/` as it was non-functional.

### Directory Structure

```
src/causaganha/       # Main package (Canonical V2)
├── cli.py           # Main CLI entry point
├── api/             # PJe API client (httpx + Pydantic)
├── storage/         # Ibis + DuckDB data layer
├── analysis/        # Pydantic AI decision analyzer
├── pipeline/        # Orchestration (collect, analyze, score)
└── utils/           # Structured logging
legacy_archive/      # Archived V1 code (Do not use)
```

## Project Overview

CausaGanha is an automated judicial decision analysis platform. It extracts, analyzes, and scores judicial decisions from Brazilian tribunals using Google's Gemini LLM with local DuckDB storage.

## Development Setup

```bash
uv venv
source .venv/bin/activate
uv sync --dev
uv pip install -e .
```

## Development Flow

CausaGanha follows a **plan-first development approach**:

### 📋 **Phase 1: Planning**

1. **Create Plan Document**: New features must start as a plan in `/docs/plans/feature-name.md`
2. **Problem Context**: Explain the problem, solution, and steps.

### 🚀 **Phase 2: Implementation**

1. **Test-Driven**: Create tests in `tests/` first.
2. **Implement**: Code in `src/causaganha/`.
3. **Verify**: Run `uv run pytest`.

## Core Commands (V2)

```bash
# Run CLI
uv run causaganha --help
```

## Architecture Overview

**Style**: Modular Monolith (Hexagonal-ish).

*   **Domain**: `src/causaganha/analysis` (Pure logic)
*   **Application**: `src/causaganha/pipeline` (Orchestration)
*   **Infrastructure**: `src/causaganha/storage` (Ibis), `src/causaganha/api` (HTTP)

## 🤖 **Agent Registry System**

CausaGanha implements a parallel development system using an agent registry in `.agents/`.
See `.agents/README.md` for detailed communication guidelines.
