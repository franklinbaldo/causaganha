# CausaGanha v2 - Architecture

This directory contains the v2 implementation of CausaGanha with PJe API integration.

## Directory Structure

```
v2/
├── api/                  # PJe Communications API client
│   ├── client.py        # httpx-based async API client
│   └── models.py        # Pydantic models for API responses
├── storage/             # Ibis + DuckDB data layer
│   ├── connection.py    # DuckDB connection via Ibis
│   ├── schema.py        # Table definitions
│   └── queries.py       # Common analytical queries
├── analysis/            # Pydantic AI decision analysis
│   ├── analyzer.py      # Decision analyzer with structured outputs
│   └── models.py        # DecisionAnalysis Pydantic model
├── pipeline/            # Data pipeline orchestration
│   ├── collect.py       # Metadata collection from API
│   ├── analyze.py       # PDF analysis workflow
│   └── score.py         # OpenSkill rating calculation
└── utils/
    └── logging.py       # Structured logging with structlog
```

## Technology Stack

### New Dependencies (v2)
- **Pydantic AI**: LLM provider abstraction with structured outputs
- **Ibis Framework**: Fast analytical queries (10-100x faster than pandas)
- **httpx**: Async HTTP client for PJe API
- **structlog**: Structured logging

### Preserved from v1
- **DuckDB**: Analytical database
- **google-generativeai**: Gemini LLM (via Pydantic AI)
- **OpenSkill**: Rating algorithm (unchanged)
- **Internet Archive**: Distribution platform

## Development Approach

v2 is being developed in **parallel** with v1:

1. **Phase 1-3 (Weeks 1-3)**: Build v2 components with TDD
2. **Phase 4 (Week 4)**: Integration testing
3. **Phase 5 (Week 5)**: Parallel production run (v1 + v2)
4. **Phase 6 (Week 6)**: Switch to v2 as primary
5. **Phase 7-8 (Weeks 7-8)**: Expand to more courts
6. **Phase 9 (Week 9)**: Remove v1 code

## Key Changes from v1

### What Changes
- **Metadata Collection**: Web scraping → PJe API (JSON)
- **Data Operations**: pandas → Ibis (10-100x faster)
- **LLM Integration**: Direct Gemini SDK → Pydantic AI (provider-agnostic)
- **Coverage**: TJRO only → 90+ courts with PJe

### What Stays the Same
- OpenSkill rating algorithm
- AI-powered decision analysis (still reads PDFs)
- DuckDB + Internet Archive architecture
- Async processing model
- GitHub Actions automation

## Hybrid Approach

The PJe API provides **metadata** (lawyer names, OABs, process numbers), but we still need **AI analysis** to determine case outcomes (who won/lost).

```
PJe API → Metadata (structured JSON)
    ↓
Store in DuckDB
    ↓
Pydantic AI + Gemini → Read PDFs → Extract outcomes
    ↓
OpenSkill → Calculate ratings
    ↓
Internet Archive → Publish rankings
```

## Getting Started

See `/docs/causaganha-v2-plan-from-scratch.md` for the complete implementation plan.

## Status

**Current Phase**: Preparation (directory structure created)
**Next Steps**: Implement PJe API client with TDD approach
