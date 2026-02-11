# CausaGanha v2 - Refactoring Plan
## Enhancing Judicial Analytics with PJe API Integration

**Version:** 2.0
**Date:** December 2024
**Status:** Planning Phase

---

## Table of Contents

1. [Understanding CausaGanha](#understanding-causaganha)
2. [Why Refactor?](#why-refactor)
3. [What Changes, What Stays](#what-changes-what-stays)
4. [The Hybrid Approach](#the-hybrid-approach)
5. [New Technology Stack](#new-technology-stack)
6. [Architecture Overview](#architecture-overview)
7. [Data Pipeline Design](#data-pipeline-design)
8. [Database Schema](#database-schema)
9. [Implementation Components](#implementation-components)
10. [Migration Strategy](#migration-strategy)
11. [Testing Approach](#testing-approach)
12. [Timeline](#timeline)
13. [Risks & Mitigation](#risks-mitigation)
14. [Success Metrics](#success-metrics)

---

## Understanding CausaGanha

### What It Actually Is

**CausaGanha** is a distributed judicial analytics platform that:

1. **Collects** judicial decisions from Brazilian courts (currently TJRO)
2. **Analyzes** decisions using AI to extract lawyer performance data
3. **Rates** lawyers using the OpenSkill algorithm (like Elo for chess)
4. **Distributes** results openly via Internet Archive

### The Core Innovation

CausaGanha applies skill rating algorithms (OpenSkill) to judicial outcomes, creating **transparent, data-driven lawyer rankings** based on actual case results.

### Current Pipeline (v1)

```
Diário PDFs → Download → AI Analysis (Gemini) → Extract Win/Loss → OpenSkill → Rankings
                ↓
         Internet Archive (for distribution)
                ↓
         DuckDB (analytical database)
```

### What It's NOT

- ❌ Not a deadline management system
- ❌ Not a practice management tool
- ❌ Not a document management system
- ❌ Not a notification service for lawyers

### Target Users

- **Researchers**: Academic studies on judicial performance
- **Journalists**: Transparency and accountability reporting
- **Public**: Access to objective lawyer performance data
- **Legal Profession**: Data-driven insights into case outcomes

---

## Why Refactor?

### Current Problems

#### 1. **Data Collection is Brittle**

**Problem**: Web scraping diários (judicial gazettes) breaks frequently
- Court websites change layout
- PDF formats vary
- No structured metadata
- Slow and unreliable

**Impact**:
- Missed data collection
- Manual fixes needed
- Limited to TJRO
- Can't scale to other courts

#### 2. **Limited Court Coverage**

**Problem**: Each court needs custom scraping logic
- Different websites
- Different formats
- Different publication schedules

**Impact**:
- Only TJRO is covered
- 90+ courts remain untapped
- No national rankings possible
- Limited research value

#### 3. **Missing Metadata**

**Problem**: Scraping diários gives us PDFs but poor metadata
- Lawyer names require extraction from PDF
- OAB numbers must be parsed
- Process numbers may be unclear
- Party associations are ambiguous

**Impact**:
- Lower data quality
- More AI extraction needed
- Higher costs (more LLM calls)
- More errors

#### 4. **Performance Issues**

**Problem**: Pandas is slow for analytical queries
- Loads entire datasets into memory
- Inefficient aggregations
- No query optimization

**Impact**:
- Slow analytics
- High memory usage
- Difficult to scale

### The Opportunity

**PJe Communications API** provides:
- ✅ Official government API (reliable)
- ✅ Structured JSON metadata (lawyer names, OABs, process numbers)
- ✅ Links to PDFs (for decision analysis)
- ✅ National coverage (90+ courts using PJe)
- ✅ Real-time access
- ✅ No scraping needed

**This changes everything** - we can get better metadata reliably and scale nationally.

### API in Action: Concrete Example

#### Making API Requests

The PJe Communications API is a standard REST API that returns structured JSON. Here's a real example:

```bash
curl -X 'GET' \
  'https://comunicaapi.pje.jus.br/api/v1/comunicacao?dataDisponibilizacaoInicio=2025-01-01&dataDisponibilizacaoFim=2025-12-31&siglaTribunal=TJRO&pagina=1&itensPorPagina=100&meio=D' \
  -H 'accept: application/json'
```

**Query Parameters:**
- `dataDisponibilizacaoInicio` / `dataDisponibilizacaoFim`: Date range filter
- `siglaTribunal`: Court code (e.g., TJRO, TJMT, TJSP)
- `pagina`: Page number (starts at 1)
- `itensPorPagina`: Results per page (max 100)
- `meio`: Communication method (`D` = Diário de Justiça Eletrônico)

#### Response Structure

The API returns structured JSON with **all the metadata we need**:

```json
{
  "status": "success",
  "message": "Sucesso",
  "count": 10000,
  "items": [
    {
      "id": 485348463,
      "data_disponibilizacao": "2025-12-12",
      "siglaTribunal": "TJRO",
      "tipoComunicacao": "Intimação",
      "nomeOrgao": "Rolim de Moura - 1ª Vara Cível",
      "idOrgao": 928,
      "numero_processo": "70009673320258220010",
      "numeroprocessocommascara": "7000967-33.2025.8.22.0010",
      "nomeClasse": "PROCEDIMENTO COMUM CÍVEL",
      "codigoClasse": "7",
      "texto": "Poder Judiciário TRIBUNAL DE JUSTIÇA...",
      "link": "https://pjepg.tjro.jus.br/pje/Processo/ConsultaDocumento/...",
      "hash": "MlkWByzDGYzEtkhvTQm98qZebmAjON",
      "status": "P",
      "destinatarios": [
        {
          "comunicacao_id": 485348463,
          "nome": "JUAREZ MOREIRA DE SOUZA",
          "polo": "A"
        }
      ],
      "destinatarioadvogados": [
        {
          "id": 844498057,
          "comunicacao_id": 485348463,
          "advogado_id": 1056180,
          "advogado": {
            "id": 1056180,
            "nome": "ONEIR FERREIRA DE SOUZA",
            "numero_oab": "6475A",
            "uf_oab": "RO"
          }
        },
        {
          "id": 844498058,
          "comunicacao_id": 485348463,
          "advogado_id": 4512552,
          "advogado": {
            "id": 4512552,
            "nome": "CIDINEIA GOMES DA ROCHA BOSCOLO",
            "numero_oab": "6594A",
            "uf_oab": "RO"
          }
        }
      ]
    }
  ]
}
```

#### Critical Implications for v2 Architecture

This structured API response **fundamentally changes** how CausaGanha collects and processes data:

##### 1. **Metadata Extraction: API → No LLM Needed**

**v1 Approach (Current):**
```
PDF Download → Gemini LLM → Extract lawyer names → Parse OAB → Normalize names
Cost: ~$0.001/page for extraction + complex parsing logic
Accuracy: 85-90% (OCR/parsing errors, name variations)
```

**v2 Approach (With API):**
```
API Call → JSON Parse → Direct field access
Cost: FREE (no LLM needed for metadata)
Accuracy: 99%+ (official structured data)
```

**Impact:**
- 🎯 **Save 50-70% on LLM costs** (only use LLM for decision outcome analysis)
- ⚡ **10x faster metadata collection** (no PDF parsing)
- 📊 **Perfect lawyer associations** (`polo: "A"` = active side, structured OAB numbers)

##### 2. **Data Quality: From Extraction to Structured Fields**

**What we get directly from API (no parsing needed):**
- ✅ `numero_processo`: Exact process number (both formats)
- ✅ `destinatarioadvogados[].advogado.nome`: Official lawyer names
- ✅ `destinatarioadvogados[].advogado.numero_oab`: OAB numbers (already formatted)
- ✅ `destinatarioadvogados[].advogado.uf_oab`: OAB jurisdiction
- ✅ `destinatarios[].polo`: Party side (`A` = active, `P` = passive)
- ✅ `nomeClasse` + `codigoClasse`: Case type (for filtering)
- ✅ `link`: Direct PDF URL (when needed for outcome analysis)

**What this eliminates:**
- ❌ No more name normalization heuristics
- ❌ No more OAB regex parsing
- ❌ No more ambiguous party associations
- ❌ No more "best guess" for process numbers

##### 3. **Scaling to 90+ Courts: Just Change One Parameter**

**v1 (Current):** Each tribunal requires custom scraper
```python
# Different scraper for each court
tjro_scraper = TJROScraper()
tjmt_scraper = TJMTScraper()  # Would need to build
tjsp_scraper = TJSPScraper()  # Would need to build
```

**v2 (With API):** Same code works for all PJe courts
```python
# Same client for all courts
client = PJeAPIClient()
await client.get_intimations_by_court("TJRO")  # Works
await client.get_intimations_by_court("TJMT")  # Works
await client.get_intimations_by_court("TJSP")  # Works
# ... 87 more courts with ZERO additional code
```

**Impact:**
- 🚀 **National coverage in Phase 7-9** (not hypothetical, just configuration)
- 📈 **100x more data** (from 1 court to 90+ courts)
- 🛠️ **Zero maintenance per court** (API handles all tribunals uniformly)

##### 4. **Decision Analysis: Still Need LLM, But Smarter**

**Important:** The API provides **metadata**, not **decision outcomes**. We still need LLM for:

```
What the API gives us:           What we still need LLM for:
✅ Process number                ❌ Who won the case?
✅ Lawyer names + OAB            ❌ What was decided?
✅ Party names + sides           ❌ Favorable/unfavorable outcome?
✅ Case class                    ❌ Full/partial win?
✅ Court/judge

LLM Role in v2:
- Read PDF from `link` field
- Analyze decision text only
- Return: winner side ("A" or "P") + confidence
```

**Cost Optimization:**
```
v1: LLM for (metadata extraction + outcome analysis) = $0.001/page
v2: LLM for (outcome analysis only) = $0.0005/page = 50% savings
```

##### 5. **Pipeline Efficiency: Parallel Processing**

**v1 Sequential Processing:**
```
Download PDF → Extract metadata → Analyze outcome → Store
     ↓              ↓                   ↓              ↓
  Slow (IO)    Slow (LLM)         Slow (LLM)      Fast
```

**v2 Parallel Processing:**
```
API → Store metadata (instant)
 ↓
Link to PDF → Analyze outcome → Update record
                    ↓                ↓
               Slow (LLM)         Fast
```

**Impact:**
- ⚡ **Instant metadata storage** (no waiting for PDF/LLM)
- 🔄 **Decouple collection from analysis** (process 1000s of metadata records, analyze PDFs later)
- 📊 **Early insights** (see lawyer activity before outcomes analyzed)

##### 6. **Data Completeness: No Missing Metadata**

**v1 Problem:** If LLM extraction fails → lose entire record
**v2 Solution:** API metadata always complete → only lose outcome analysis if LLM fails

**Example:**
```
Scenario: 100 intimations from API, 5 PDFs unreachable

v1 Result:
- 95 complete records (95%)
- 5 total losses

v2 Result:
- 100 records with metadata (100%)
- 95 with outcome analysis
- 5 pending outcome (can retry later without re-downloading metadata)
```

---

## What Changes, What Stays

### ✅ What STAYS (Core System)

1. **OpenSkill Rating System**
   - The mathematical algorithm stays exactly the same
   - Still rating lawyers based on win/loss outcomes
   - Still using μ (mu) and σ (sigma) parameters

2. **DuckDB + Internet Archive**
   - Keep distributed architecture
   - Keep DuckDB for analytics
   - Keep publishing to Internet Archive

3. **Async Processing**
   - Keep async/concurrent processing model
   - Keep batch processing approach

4. **GitHub Actions Automation**
   - Keep automated workflows
   - Keep scheduled runs

5. **AI Analysis of Decisions**
   - **Still need to read PDFs with LLM**
   - **Still need to determine who won/lost**
   - Still need to extract case outcomes

### 🔄 What CHANGES (Data Collection & Tools)

1. **Metadata Collection**
   - FROM: Scraping diários HTML/PDFs
   - TO: PJe Communications API (JSON)

2. **Data Operations**
   - FROM: Pandas
   - TO: Ibis (10-100x faster)

3. **LLM Integration**
   - FROM: Direct Google Gemini SDK
   - TO: Pydantic AI (provider-agnostic)

4. **Coverage**
   - FROM: Only TJRO
   - TO: All PJe-enabled courts (90+)

5. **Data Quality**
   - FROM: Extracted lawyer names/OABs from text
   - TO: Structured lawyer associations from API

### ❌ What's REMOVED

1. **Web Scraping Libraries**
   - Remove: BeautifulSoup, Selenium, Scrapy
   - Why: API provides structured data

2. **Pandas**
   - Remove: pandas (for analytical queries)
   - Why: Ibis is faster and more efficient

---

## The Hybrid Approach

### Critical Understanding

The PJe API gives us **metadata**, not **analysis**:

| Data Type | Source | Example |
|-----------|--------|---------|
| **Metadata** | PJe API | Process number, lawyer names, OAB numbers, dates, parties |
| **PDF Link** | PJe API | URL to the decision document |
| **Win/Loss** | AI Analysis (LLM) | Who won, who lost, decision type, reasoning |

### Why We Still Need AI

**The API does NOT tell us:**
- ❌ Who won the case
- ❌ Who lost the case
- ❌ Decision reasoning
- ❌ Case outcomes

**We must read the actual PDF decision** to determine outcomes for ratings.

### The New Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     METADATA COLLECTION (New)                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
            PJe API → Structured JSON
                ↓                    ↓
         Process Numbers      Lawyer Associations
         Court Info          OAB Numbers
         Dates               Party Names
         PDF Links           ←─────────┘
                ↓
         Store in DuckDB (metadata table)
                ↓
┌─────────────────────────────────────────────────────────────────┐
│                  DECISION ANALYSIS (Unchanged)                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
          For each PDF link:
                ↓
          Pydantic AI + Gemini
                ↓
          Read PDF → Extract:
          - Winner OAB
          - Loser OAB
          - Decision type
          - Outcome
          - Reasoning
                ↓
         Store in DuckDB (analysis table)
                ↓
┌─────────────────────────────────────────────────────────────────┐
│                    RATING CALCULATION (Same)                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
          OpenSkill Algorithm
                ↓
          Updated Ratings
                ↓
          Publish to Internet Archive
```

### Benefits of Hybrid Approach

1. **Better Metadata** (from API)
   - Reliable lawyer-case associations
   - Accurate OAB numbers
   - Clean process numbers
   - No extraction errors

2. **Better Analysis** (from AI)
   - Focus AI on what matters (outcomes)
   - Don't waste AI calls on metadata extraction
   - Lower costs
   - Higher quality

3. **Scalability**
   - API handles 90+ courts
   - AI only analyzes decisions (not metadata)
   - Can process thousands of cases

---

## New Technology Stack

### Core Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.11"

# Data Operations (NEW - replacing Pandas)
ibis-framework = {extras = ["duckdb"], version = "^9.0"}

# API Client (NEW)
httpx = "^0.27"  # Async HTTP client for PJe API

# AI Integration (NEW - replacing direct Gemini SDK)
pydantic-ai = "^0.0.14"  # LLM abstraction with structured outputs
pydantic = "^2.10"  # Data validation

# Keep Existing
duckdb = "^0.9"  # Analytical database
google-generativeai = "^0.3"  # Still used by Pydantic AI for Gemini

# Utilities
python-dotenv = "^1.0"
structlog = "^24.1"  # Better logging
rich = "^13.7"  # CLI formatting
typer = "^0.15"  # CLI framework (optional improvement)
```

### Remove (No Longer Needed)

```toml
# Web scraping (API replaces this)
beautifulsoup4 = "^4.12"  # ❌ Remove
lxml = "^4.9"  # ❌ Remove
selenium = "^4.15"  # ❌ Remove
scrapy = "^2.11"  # ❌ Remove

# Data operations (Ibis replaces this)
pandas = "^1.5"  # ❌ Remove (for analytical queries)
# Note: May keep pandas if used elsewhere, but replace in analytics
```

### Why These Choices?

#### Pydantic AI
**Chosen over direct Gemini SDK because:**
- ✅ Provider-agnostic (easy to switch to Claude, GPT-4, etc.)
- ✅ Structured outputs with Pydantic models (type-safe)
- ✅ Built-in validation of LLM responses
- ✅ Retry logic and error handling
- ✅ Better for production systems

**Example:**
```python
# OLD: Direct Gemini
response = gemini.generate_content(pdf)
# Parse unstructured text, hope for the best

# NEW: Pydantic AI
class DecisionAnalysis(BaseModel):
    winner_oab: str
    loser_oab: str
    outcome: str

agent = Agent('google-gla:gemini-2.5-flash', result_type=DecisionAnalysis)
result = await agent.run(pdf_url)
# Guaranteed structured output, validated
```

#### Ibis
**Chosen over Pandas because:**
- ✅ 10-100x faster for analytical queries
- ✅ Lazy evaluation (optimizes before execution)
- ✅ Works with DuckDB natively
- ✅ Much lower memory usage
- ✅ Same API can target PostgreSQL, BigQuery later

**Example:**
```python
# OLD: Pandas (slow)
df = pd.read_sql("SELECT * FROM intimations", conn)
result = df[df['tribunal'] == 'TJRO'].groupby('lawyer').count()

# NEW: Ibis (fast)
intimations = con.table('intimations')
result = (
    intimations
    .filter(_.tribunal == 'TJRO')
    .group_by('lawyer')
    .count()
    .execute()
)
# Query optimized, uses DuckDB's native speed
```

#### httpx
**Chosen over requests because:**
- ✅ Native async support (works with asyncio)
- ✅ HTTP/2 support
- ✅ Connection pooling
- ✅ Better for concurrent API calls

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         CausaGanha v2                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  1. METADATA COLLECTION (New)                             │ │
│  │                                                            │ │
│  │  PJe API Client (httpx)                                   │ │
│  │  └─→ GET /comunicacao?siglaTribunal=TJRO                 │ │
│  │      └─→ Returns: JSON with metadata + PDF links         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  2. DATA STORAGE (Improved)                               │ │
│  │                                                            │ │
│  │  Ibis + DuckDB                                            │ │
│  │  ├─→ intimations table (metadata from API)               │ │
│  │  ├─→ intimation_lawyers table (associations)             │ │
│  │  └─→ decision_analysis table (AI results)                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  3. DECISION ANALYSIS (Enhanced)                          │ │
│  │                                                            │ │
│  │  Pydantic AI Agent                                        │ │
│  │  └─→ Model: google-gla:gemini-2.5-flash                  │ │
│  │      └─→ Read PDF → Extract structured data              │ │
│  │          └─→ DecisionAnalysis (Pydantic model)           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  4. RATING CALCULATION (Unchanged)                        │ │
│  │                                                            │ │
│  │  OpenSkill Algorithm                                      │ │
│  │  └─→ Update lawyer ratings based on outcomes             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  5. DISTRIBUTION (Unchanged)                              │ │
│  │                                                            │ │
│  │  Internet Archive                                         │ │
│  │  └─→ Publish DuckDB file with rankings                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ORCHESTRATION (Unchanged)                                │ │
│  │                                                            │ │
│  │  GitHub Actions                                           │ │
│  │  └─→ Scheduled workflows                                  │ │
│  │      ├─→ Daily: Collect new intimations (API)            │ │
│  │      ├─→ Hourly: Analyze pending PDFs (AI)               │ │
│  │      └─→ Daily: Recalculate ratings (OpenSkill)          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Project Structure

```
causaganha/
├── src/
│   └── causaganha/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point (existing)
│       │
│       ├── v2/                 # NEW: v2 implementation
│       │   ├── __init__.py
│       │   ├── config.py       # Configuration with Pydantic Settings
│       │   │
│       │   ├── api/            # NEW: PJe API client
│       │   │   ├── __init__.py
│       │   │   ├── client.py   # httpx-based API client
│       │   │   └── models.py   # Pydantic models for API responses
│       │   │
│       │   ├── storage/        # NEW: Ibis-based storage
│       │   │   ├── __init__.py
│       │   │   ├── connection.py  # DuckDB connection via Ibis
│       │   │   ├── schema.py      # Table definitions
│       │   │   └── queries.py     # Common analytical queries
│       │   │
│       │   ├── analysis/       # NEW: Pydantic AI analysis
│       │   │   ├── __init__.py
│       │   │   ├── analyzer.py    # Decision analyzer with Pydantic AI
│       │   │   └── models.py      # DecisionAnalysis output model
│       │   │
│       │   ├── pipeline/       # NEW: Orchestration
│       │   │   ├── __init__.py
│       │   │   ├── collect.py     # Metadata collection from API
│       │   │   ├── analyze.py     # PDF analysis workflow
│       │   │   └── score.py       # Rating calculation
│       │   │
│       │   └── utils/
│       │       ├── __init__.py
│       │       └── logging.py     # Structured logging setup
│       │
│       ├── legacy/             # Existing v1 code (keep for now)
│       │   ├── ...
│       │   └── (current implementation)
│       │
│       └── scoring/            # OpenSkill (unchanged)
│           └── openskill.py
│
├── tests/
│   ├── v2/                     # NEW: Tests for v2
│   │   ├── test_api_client.py
│   │   ├── test_storage.py
│   │   ├── test_analyzer.py
│   │   └── test_pipeline.py
│   └── legacy/                 # Existing tests
│
├── scripts/                    # NEW: Migration and utility scripts
│   ├── migrate_v1_to_v2.py    # Data migration script
│   └── validate_api_coverage.py  # Check which courts have API access
│
├── .github/
│   └── workflows/
│       ├── v2_daily_collect.yml    # NEW: Daily metadata collection
│       ├── v2_hourly_analyze.yml   # NEW: Hourly PDF analysis
│       └── v2_daily_score.yml      # NEW: Daily rating updates
│
├── pyproject.toml              # Updated dependencies
├── .env.example                # Updated with new API keys
└── README.md                   # Updated documentation
```

---

## Data Pipeline Design

### Pipeline Stages

#### Stage 1: Metadata Collection (NEW)

**What**: Fetch intimations metadata from PJe API

**Frequency**: Daily (can be more frequent)

**Input**: None (pulls from API)

**Process**:
1. Query PJe API for configured courts (e.g., TJRO, TJMT)
2. Get last sync date from database
3. Fetch intimations since last sync
4. Validate with Pydantic models
5. Store metadata in `intimations` table
6. Extract lawyer associations to `intimation_lawyers` table

**Output**: Metadata records in DuckDB

**Code Structure**:
```python
# src/causaganha/v2/pipeline/collect.py

from ..api.client import PJeAPIClient
from ..storage.connection import get_connection
from datetime import date, timedelta

async def collect_metadata_for_court(
    tribunal: str,
    days_back: int = 7
) -> int:
    """
    Collect intimation metadata from PJe API

    Returns:
        Number of new intimations collected
    """
    client = PJeAPIClient()
    con = get_connection()

    # Get date range
    data_inicio = date.today() - timedelta(days=days_back)

    # Fetch from API
    intimations = await client.get_intimations_by_court(
        sigla_tribunal=tribunal,
        data_inicio=data_inicio
    )

    # Store in database
    new_count = store_intimations(con, intimations)

    return new_count
```

#### Stage 2: PDF Analysis (ENHANCED)

**What**: Analyze decision PDFs to extract win/loss outcomes

**Frequency**: Continuous/Hourly (process pending)

**Input**: PDF URLs from `intimations` table where `analyzed = false`

**Process**:
1. Query unanalyzed intimations
2. For each PDF URL:
   a. Call Pydantic AI agent with PDF URL
   b. Gemini reads PDF natively
   c. Extract structured DecisionAnalysis
   d. Validate with Pydantic model
3. Store results in `decision_analysis` table
4. Mark intimation as analyzed

**Output**: DecisionAnalysis records in DuckDB

**Code Structure**:
```python
# src/causaganha/v2/pipeline/analyze.py

from ..analysis.analyzer import DecisionAnalyzer
from ..storage.connection import get_connection

async def analyze_pending_decisions(
    batch_size: int = 10
) -> int:
    """
    Analyze pending PDFs in batches

    Returns:
        Number of decisions analyzed
    """
    con = get_connection()
    analyzer = DecisionAnalyzer()

    # Get pending intimations
    pending = get_unanalyzed_intimations(con, limit=batch_size)

    # Analyze in parallel
    results = await analyzer.analyze_batch(
        [p.pdf_url for p in pending]
    )

    # Store results
    analyzed_count = store_analysis_results(con, results)

    return analyzed_count
```

#### Stage 3: Rating Calculation (UNCHANGED)

**What**: Update OpenSkill ratings based on new outcomes

**Frequency**: Daily (after analysis)

**Input**: New `decision_analysis` records

**Process**:
1. Get all new analyses since last rating update
2. For each decision:
   a. Get current ratings for winner and loser
   b. Calculate new ratings with OpenSkill
   c. Update `lawyer_ratings` table
3. Recalculate global rankings

**Output**: Updated ratings in DuckDB

**Note**: This uses existing OpenSkill implementation, no changes needed.

#### Stage 4: Distribution (UNCHANGED)

**What**: Publish updated database to Internet Archive

**Frequency**: Daily

**Process**:
1. Export DuckDB file
2. Upload to Internet Archive
3. Update metadata

**Note**: Uses existing implementation, no changes needed.

### Workflow Diagram

```
┌──────────────────┐
│  GitHub Actions  │
│  Scheduler       │
└────────┬─────────┘
         │
         ├─→ Daily 00:00 UTC
         │   └─→ collect_metadata()
         │       └─→ PJe API
         │           └─→ Store in DuckDB
         │
         ├─→ Every Hour
         │   └─→ analyze_pending_decisions()
         │       └─→ Pydantic AI + Gemini
         │           └─→ Read PDFs
         │               └─→ Store analyses
         │
         └─→ Daily 23:00 UTC
             └─→ calculate_ratings()
                 └─→ OpenSkill
                     └─→ Update ratings
                         └─→ Publish to Internet Archive
```

---

## Database Schema

### Table Design

```sql
-- Monitored courts
CREATE TABLE monitored_courts (
    sigla_tribunal VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Intimations metadata (from PJe API)
CREATE TABLE intimations (
    -- From API
    id BIGINT PRIMARY KEY,
    numero_processo VARCHAR(25) NOT NULL,
    numeroprocessocommascara VARCHAR(30),
    data_disponibilizacao DATE NOT NULL,
    sigla_tribunal VARCHAR(10) NOT NULL,
    id_orgao INTEGER,
    tipo_comunicacao VARCHAR(50),
    nome_orgao VARCHAR(255),
    texto TEXT,
    link VARCHAR(500),
    tipo_documento VARCHAR(100),
    nome_classe VARCHAR(255),
    codigo_classe VARCHAR(10),
    hash VARCHAR(100) UNIQUE,
    status VARCHAR(1),

    -- Analysis tracking
    analyzed BOOLEAN DEFAULT FALSE,
    analysis_attempted_at TIMESTAMP,
    analysis_error TEXT,
    analyzed_at TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Lawyer associations (extracted from API destinatarioadvogados)
CREATE TABLE intimation_lawyers (
    intimation_id BIGINT REFERENCES intimations(id),
    oab_number VARCHAR(20) NOT NULL,
    oab_state VARCHAR(2) NOT NULL,
    lawyer_name VARCHAR(255),
    polo VARCHAR(1),  -- 'A' = autor, 'P' = réu, etc.

    PRIMARY KEY (intimation_id, oab_number, oab_state)
);

-- Parties (extracted from API destinatarios)
CREATE TABLE intimation_parties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intimation_id BIGINT REFERENCES intimations(id),
    party_name VARCHAR(255) NOT NULL,
    polo VARCHAR(1),

    created_at TIMESTAMP DEFAULT NOW()
);

-- Decision analysis (from Pydantic AI)
CREATE TABLE decision_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intimation_id BIGINT REFERENCES intimations(id) UNIQUE,

    -- Winner info
    winner_lawyer_oab VARCHAR(20) NOT NULL,
    winner_lawyer_state VARCHAR(2) NOT NULL,
    winner_party_name VARCHAR(255),

    -- Loser info
    loser_lawyer_oab VARCHAR(20) NOT NULL,
    loser_lawyer_state VARCHAR(2) NOT NULL,
    loser_party_name VARCHAR(255),

    -- Decision details
    decision_type VARCHAR(50),
    outcome VARCHAR(50),
    judge_name VARCHAR(255),
    decision_reasoning TEXT,

    -- Quality metrics
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),

    -- Model info
    model_used VARCHAR(50),
    model_provider VARCHAR(20),
    analysis_duration_seconds FLOAT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Lawyer ratings (OpenSkill - existing, may need adjustments)
CREATE TABLE lawyer_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    oab_number VARCHAR(20) NOT NULL,
    oab_state VARCHAR(2) NOT NULL,
    lawyer_name VARCHAR(255),

    -- OpenSkill parameters
    mu FLOAT NOT NULL DEFAULT 25.0,
    sigma FLOAT NOT NULL DEFAULT 8.333,

    -- Derived rating (conservative estimate)
    rating FLOAT GENERATED ALWAYS AS (mu - 3 * sigma) STORED,

    -- Statistics
    total_cases INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    win_rate FLOAT GENERATED ALWAYS AS (
        CASE WHEN total_cases > 0
        THEN CAST(wins AS FLOAT) / total_cases
        ELSE 0 END
    ) STORED,

    -- Context
    tribunal VARCHAR(10),  -- NULL for global rating

    last_updated TIMESTAMP DEFAULT NOW(),

    UNIQUE(oab_number, oab_state, tribunal)
);

-- Sync/processing log
CREATE TABLE sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(20) NOT NULL,  -- 'collect', 'analyze', 'score'
    entity_id VARCHAR(100),  -- tribunal or batch identifier

    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,

    items_processed INTEGER DEFAULT 0,
    items_succeeded INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,

    status VARCHAR(20) NOT NULL,  -- 'running', 'success', 'failed', 'partial'
    error_message TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_intimations_tribunal_date
    ON intimations(sigla_tribunal, data_disponibilizacao DESC);

CREATE INDEX idx_intimations_unanalyzed
    ON intimations(analyzed, data_disponibilizacao)
    WHERE analyzed = FALSE;

CREATE INDEX idx_intimation_lawyers_oab
    ON intimation_lawyers(oab_number, oab_state);

CREATE INDEX idx_decision_winner
    ON decision_analysis(winner_lawyer_oab, winner_lawyer_state);

CREATE INDEX idx_decision_loser
    ON decision_analysis(loser_lawyer_oab, loser_lawyer_state);

CREATE INDEX idx_lawyer_ratings_ranking
    ON lawyer_ratings(tribunal, rating DESC)
    WHERE tribunal IS NOT NULL;

CREATE INDEX idx_lawyer_ratings_global
    ON lawyer_ratings(rating DESC)
    WHERE tribunal IS NULL;
```

### Data Flow Example

```sql
-- 1. API returns intimation
INSERT INTO intimations (
    id, numero_processo, sigla_tribunal, link, analyzed
) VALUES (
    123456, '0001234-56.2024.8.22.0001', 'TJRO',
    'https://pje.tjro.jus.br/doc/12345.pdf', FALSE
);

-- 2. API returns lawyer association
INSERT INTO intimation_lawyers (
    intimation_id, oab_number, oab_state, lawyer_name
) VALUES (
    123456, '5733', 'RO', 'FRANKLIN SILVEIRA BALDO'
);

-- 3. Pydantic AI analyzes PDF
INSERT INTO decision_analysis (
    intimation_id,
    winner_lawyer_oab, winner_lawyer_state,
    loser_lawyer_oab, loser_lawyer_state,
    outcome, confidence_score
) VALUES (
    123456,
    '5733', 'RO',
    '6789', 'RO',
    'procedente', 0.95
);

-- 4. Mark as analyzed
UPDATE intimations
SET analyzed = TRUE, analyzed_at = NOW()
WHERE id = 123456;

-- 5. OpenSkill updates ratings
-- (existing algorithm processes decision_analysis)
UPDATE lawyer_ratings
SET mu = 26.2, sigma = 7.8, total_cases = total_cases + 1, wins = wins + 1
WHERE oab_number = '5733' AND oab_state = 'RO';
```

---

## Implementation Components

### 1. PJe API Client

**File**: `src/causaganha/v2/api/client.py`

```python
"""PJe Communications API client with httpx"""

import httpx
import structlog
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field

logger = structlog.get_logger()

# Pydantic models for API responses
class LawyerInfo(BaseModel):
    """Lawyer information from API"""
    id: int
    nome: str
    numero_oab: str
    uf_oab: str

class DestinarioAdvogado(BaseModel):
    """Lawyer association"""
    advogado: LawyerInfo

class Destinatario(BaseModel):
    """Party information"""
    nome: str
    polo: str  # 'A', 'P', etc.

class Intimation(BaseModel):
    """Complete intimation from API"""
    id: int
    numero_processo: str
    numeroprocessocommascara: Optional[str] = None
    data_disponibilizacao: str
    siglaTribunal: str = Field(alias='siglaTribunal')
    idOrgao: Optional[int] = Field(None, alias='idOrgao')
    tipoComunicacao: str = Field(alias='tipoComunicacao')
    nomeOrgao: str = Field(alias='nomeOrgao')
    texto: str
    link: str
    tipoDocumento: str = Field(alias='tipoDocumento')
    nomeClasse: str = Field(alias='nomeClasse')
    codigoClasse: Optional[str] = Field(None, alias='codigoClasse')
    hash: str
    status: str
    destinatarioadvogados: List[DestinarioAdvogado] = []
    destinatarios: List[Destinatario] = []

    class Config:
        populate_by_name = True

class PJeAPIClient:
    """
    Client for PJe Communications API

    Handles authentication, pagination, and error handling
    """

    def __init__(
        self,
        base_url: str = "https://comunicaapi.pje.jus.br/api/v1",
        timeout: int = 30
    ):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=5)
        )

    async def get_intimations_by_court(
        self,
        sigla_tribunal: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit_per_page: int = 100
    ) -> List[Intimation]:
        """
        Fetch all intimations for a court with automatic pagination

        Args:
            sigla_tribunal: Court code (e.g., 'TJRO', 'TJMT')
            data_inicio: Start date filter
            data_fim: End date filter
            limit_per_page: Results per page (max 100)

        Returns:
            List of validated Intimation objects
        """
        all_intimations = []
        offset = 0

        while True:
            params = {
                "siglaTribunal": sigla_tribunal,
                "offset": offset,
                "limit": limit_per_page
            }

            if data_inicio:
                params["dataInicio"] = data_inicio.strftime("%Y-%m-%d")
            if data_fim:
                params["dataFim"] = data_fim.strftime("%Y-%m-%d")

            logger.info("fetching_page",
                       tribunal=sigla_tribunal,
                       offset=offset,
                       limit=limit_per_page)

            try:
                response = await self.client.get(
                    f"{self.base_url}/comunicacao",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

            except httpx.HTTPError as e:
                logger.error("api_request_failed",
                            error=str(e),
                            params=params)
                raise

            # Validate and parse
            items = data.get("items", [])
            if not items:
                logger.info("no_more_items", total_fetched=len(all_intimations))
                break

            try:
                intimations = [Intimation(**item) for item in items]
                all_intimations.extend(intimations)
                logger.info("page_fetched",
                           count=len(intimations),
                           total=len(all_intimations))

            except Exception as e:
                logger.error("validation_failed",
                            error=str(e),
                            sample=items[0] if items else None)
                raise

            # Check if more pages
            total_count = data.get("count", 0)
            if len(all_intimations) >= total_count:
                logger.info("all_pages_fetched",
                           total=len(all_intimations))
                break

            offset += limit_per_page

        return all_intimations

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
```

### 2. Ibis Storage Layer

**File**: `src/causaganha/v2/storage/connection.py`

```python
"""DuckDB connection via Ibis"""

import ibis
from ibis import _
from pathlib import Path
import structlog

logger = structlog.get_logger()

_connection = None

def get_connection(db_path: str = "data/causaganha.duckdb") -> ibis.backends.duckdb.Backend:
    """
    Get or create DuckDB connection via Ibis

    This is a singleton - returns the same connection instance
    """
    global _connection

    if _connection is None:
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info("connecting_to_duckdb", path=str(db_file))
        _connection = ibis.duckdb.connect(str(db_file))

        # Initialize schema if needed
        _initialize_schema(_connection)

    return _connection

def _initialize_schema(con: ibis.backends.duckdb.Backend):
    """Create tables if they don't exist"""

    tables = con.list_tables()

    if 'intimations' not in tables:
        logger.info("creating_schema")

        # Read schema from SQL file
        schema_file = Path(__file__).parent / "schema.sql"
        if schema_file.exists():
            schema_sql = schema_file.read_text()
            # Execute each statement
            for statement in schema_sql.split(';'):
                if statement.strip():
                    con.raw_sql(statement)
        else:
            logger.warning("schema_file_not_found",
                          path=str(schema_file))
```

**File**: `src/causaganha/v2/storage/queries.py`

```python
"""Common analytical queries using Ibis"""

import ibis
from ibis import _
from datetime import date, timedelta
import structlog

logger = structlog.get_logger()

def get_unanalyzed_intimations(
    con: ibis.backends.duckdb.Backend,
    limit: int = 100
) -> list:
    """Get intimations that need PDF analysis"""

    intimations = con.table('intimations')

    result = (
        intimations
        .filter(_.analyzed == False)
        .filter(_.link.notnull())
        .order_by(_.data_disponibilizacao.desc())
        .limit(limit)
    )

    return result.to_pandas().to_dict('records')

def store_intimations(
    con: ibis.backends.duckdb.Backend,
    intimations: list
) -> int:
    """
    Store intimations in database

    Returns count of new records inserted
    """
    if not intimations:
        return 0

    # Prepare records
    records = []
    for item in intimations:
        records.append({
            'id': item.id,
            'numero_processo': item.numero_processo,
            'numeroprocessocommascara': item.numeroprocessocommascara,
            'data_disponibilizacao': item.data_disponibilizacao,
            'sigla_tribunal': item.siglaTribunal,
            'id_orgao': item.idOrgao,
            'tipo_comunicacao': item.tipoComunicacao,
            'nome_orgao': item.nomeOrgao,
            'texto': item.texto,
            'link': item.link,
            'tipo_documento': item.tipoDocumento,
            'nome_classe': item.nomeClasse,
            'codigo_classe': item.codigoClasse,
            'hash': item.hash,
            'status': item.status,
            'analyzed': False
        })

    # Use raw SQL for upsert (Ibis doesn't have native upsert yet)
    inserted = 0
    for record in records:
        try:
            con.raw_sql(f"""
                INSERT INTO intimations (
                    id, numero_processo, numeroprocessocommascara,
                    data_disponibilizacao, sigla_tribunal, id_orgao,
                    tipo_comunicacao, nome_orgao, texto, link,
                    tipo_documento, nome_classe, codigo_classe,
                    hash, status, analyzed
                ) VALUES (
                    {record['id']},
                    '{record['numero_processo']}',
                    '{record['numeroprocessocommascara'] or ''}',
                    '{record['data_disponibilizacao']}',
                    '{record['sigla_tribunal']}',
                    {record['id_orgao'] or 'NULL'},
                    '{record['tipo_comunicacao']}',
                    '{record['nome_orgao'].replace("'", "''")}',
                    '{record['texto'].replace("'", "''")}',
                    '{record['link']}',
                    '{record['tipo_documento']}',
                    '{record['nome_classe']}',
                    '{record['codigo_classe'] or ''}',
                    '{record['hash']}',
                    '{record['status']}',
                    FALSE
                )
                ON CONFLICT (id) DO UPDATE SET
                    updated_at = CURRENT_TIMESTAMP
            """)
            inserted += 1
        except Exception as e:
            logger.warning("insert_failed",
                          intimation_id=record['id'],
                          error=str(e))

    logger.info("intimations_stored", inserted=inserted, total=len(records))
    return inserted

def store_lawyer_associations(
    con: ibis.backends.duckdb.Backend,
    intimation_id: int,
    lawyers: list
) -> int:
    """Store lawyer associations for an intimation"""

    inserted = 0
    for lawyer_data in lawyers:
        advogado = lawyer_data.get('advogado', {})

        try:
            con.raw_sql(f"""
                INSERT INTO intimation_lawyers (
                    intimation_id, oab_number, oab_state, lawyer_name
                ) VALUES (
                    {intimation_id},
                    '{advogado.get('numero_oab', '')}',
                    '{advogado.get('uf_oab', '')}',
                    '{advogado.get('nome', '').replace("'", "''")}'
                )
                ON CONFLICT DO NOTHING
            """)
            inserted += 1
        except Exception as e:
            logger.warning("lawyer_association_failed",
                          intimation_id=intimation_id,
                          error=str(e))

    return inserted

def get_recent_analyses(
    con: ibis.backends.duckdb.Backend,
    days: int = 7
) -> list:
    """Get recent decision analyses"""

    analysis = con.table('decision_analysis')

    cutoff = date.today() - timedelta(days=days)

    result = (
        analysis
        .filter(_.created_at >= cutoff)
        .order_by(_.created_at.desc())
    )

    return result.to_pandas().to_dict('records')

def get_lawyer_stats(
    con: ibis.backends.duckdb.Backend,
    oab_number: str,
    oab_state: str
) -> dict:
    """Get statistics for a specific lawyer"""

    analysis = con.table('decision_analysis')

    # Wins
    wins = (
        analysis
        .filter(_.winner_lawyer_oab == oab_number)
        .filter(_.winner_lawyer_state == oab_state)
        .count()
        .execute()
    )

    # Losses
    losses = (
        analysis
        .filter(_.loser_lawyer_oab == oab_number)
        .filter(_.loser_lawyer_state == oab_state)
        .count()
        .execute()
    )

    return {
        'oab_number': oab_number,
        'oab_state': oab_state,
        'wins': wins,
        'losses': losses,
        'total': wins + losses,
        'win_rate': wins / (wins + losses) if (wins + losses) > 0 else 0
    }
```

### 3. Pydantic AI Decision Analyzer

**File**: `src/causaganha/v2/analysis/models.py`

```python
"""Pydantic models for decision analysis"""

from pydantic import BaseModel, Field

class DecisionAnalysis(BaseModel):
    """
    Structured output from LLM analysis of a judicial decision

    This model defines exactly what we expect from the AI
    """

    winner_lawyer_oab: str = Field(
        description="OAB registration number of the winning lawyer (e.g., '5733')"
    )
    winner_lawyer_state: str = Field(
        max_length=2,
        description="State code of winner's OAB registration (e.g., 'RO')"
    )
    winner_party_name: str = Field(
        description="Full name of the winning party"
    )

    loser_lawyer_oab: str = Field(
        description="OAB registration number of the losing lawyer"
    )
    loser_lawyer_state: str = Field(
        max_length=2,
        description="State code of loser's OAB registration"
    )
    loser_party_name: str = Field(
        description="Full name of the losing party"
    )

    decision_type: str = Field(
        description=(
            "Type of decision: 'sentença' (first instance judgment), "
            "'acórdão' (appellate decision), or 'decisão interlocutória' "
            "(interlocutory decision)"
        )
    )
    outcome: str = Field(
        description=(
            "Outcome of the decision: 'procedente' (granted in full), "
            "'improcedente' (denied), or 'parcialmente procedente' (partially granted)"
        )
    )

    judge_name: str = Field(
        description="Full name of the judge or rapporteur who issued the decision"
    )

    decision_reasoning: str = Field(
        description=(
            "Brief summary of the judge's main reasoning and legal basis "
            "for the decision (2-3 sentences maximum)"
        )
    )

    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Confidence level in this analysis (0.0 to 1.0). "
            "Use lower scores if information is unclear or ambiguous."
        )
    )
```

**File**: `src/causaganha/v2/analysis/analyzer.py`

```python
"""Decision analyzer using Pydantic AI"""

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
import structlog
from typing import List, Optional
from .models import DecisionAnalysis

logger = structlog.get_logger()

class DecisionAnalyzer:
    """
    Analyze judicial decisions using Pydantic AI

    Uses Google Gemini to read PDFs natively and extract
    structured information about case outcomes
    """

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        provider: str = "google-gla"
    ):
        self.model_name = model_name
        self.provider = provider

        # System prompt for the AI
        system_prompt = """
        You are an expert Brazilian legal analyst specializing in judicial decisions.

        Your task is to read judicial decision documents and extract structured
        information about case outcomes for a lawyer performance rating system.

        CRITICAL REQUIREMENTS:
        1. Identify the winning and losing parties with precision
        2. Extract the correct OAB numbers for each lawyer
        3. Determine the decision type and outcome accurately
        4. Provide a brief summary of the judge's reasoning
        5. Use confidence_score to indicate uncertainty:
           - 0.9-1.0: Very confident, all information clear
           - 0.7-0.9: Confident, minor ambiguities
           - 0.5-0.7: Moderate confidence, some unclear elements
           - <0.5: Low confidence, significant ambiguities

        IMPORTANT NOTES:
        - OAB numbers are usually in format: "OAB/XX NNNNN" (e.g., "OAB/RO 5733")
        - In Brazilian law:
           * "Autor" or "Requerente" = plaintiff/claimant
           * "Réu" or "Requerido" = defendant/respondent
           * "Procedente" means the plaintiff won
           * "Improcedente" means the defendant won
           * "Parcialmente procedente" = partial victory (treat as plaintiff win)
        - Decision types:
           * "Sentença" = first instance judgment
           * "Acórdão" = appellate court decision
           * "Decisão interlocutória" = interlocutory decision

        If critical information is missing or unclear, reflect this in your
        confidence_score. Never guess OAB numbers - if unclear, indicate in
        confidence_score.
        """

        # Create Pydantic AI agent
        self.agent = Agent(
            f'{provider}:{model_name}',
            result_type=DecisionAnalysis,
            system_prompt=system_prompt
        )

        logger.info("analyzer_initialized",
                   model=model_name,
                   provider=provider)

    async def analyze_pdf(
        self,
        pdf_url: str,
        intimation_id: Optional[int] = None
    ) -> DecisionAnalysis:
        """
        Analyze a single PDF decision document

        Args:
            pdf_url: URL to the PDF document
            intimation_id: Optional intimation ID for logging

        Returns:
            DecisionAnalysis with extracted information

        Raises:
            Exception: If analysis fails
        """
        logger.info("analyzing_pdf",
                   url=pdf_url,
                   intimation_id=intimation_id)

        try:
            # Pydantic AI + Gemini reads PDF natively
            result = await self.agent.run(
                f"Analyze this judicial decision PDF: {pdf_url}",
                message_history=[]
            )

            # Log results
            logger.info("analysis_complete",
                       intimation_id=intimation_id,
                       winner_oab=result.data.winner_lawyer_oab,
                       loser_oab=result.data.loser_lawyer_oab,
                       decision_type=result.data.decision_type,
                       outcome=result.data.outcome,
                       confidence=result.data.confidence_score)

            return result.data

        except Exception as e:
            logger.error("analysis_failed",
                        intimation_id=intimation_id,
                        url=pdf_url,
                        error=str(e))
            raise

    async def analyze_batch(
        self,
        pdf_urls: List[str],
        intimation_ids: Optional[List[int]] = None
    ) -> List[DecisionAnalysis]:
        """
        Analyze multiple PDFs concurrently

        Args:
            pdf_urls: List of PDF URLs
            intimation_ids: Optional list of intimation IDs (same length)

        Returns:
            List of DecisionAnalysis results (only successful ones)
        """
        import asyncio

        if intimation_ids is None:
            intimation_ids = [None] * len(pdf_urls)

        logger.info("batch_analysis_start",
                   total=len(pdf_urls))

        # Create tasks
        tasks = [
            self.analyze_pdf(url, int_id)
            for url, int_id in zip(pdf_urls, intimation_ids)
        ]

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Separate successes from failures
        analyses = [r for r in results if isinstance(r, DecisionAnalysis)]
        errors = [r for r in results if isinstance(r, Exception)]

        logger.info("batch_analysis_complete",
                   total=len(pdf_urls),
                   successful=len(analyses),
                   failed=len(errors))

        return analyses
```

### 4. Pipeline Orchestration

**File**: `src/causaganha/v2/pipeline/collect.py`

```python
"""Metadata collection pipeline"""

import asyncio
import structlog
from datetime import date, timedelta
from typing import List

from ..api.client import PJeAPIClient
from ..storage.connection import get_connection
from ..storage.queries import store_intimations, store_lawyer_associations

logger = structlog.get_logger()

async def collect_metadata_for_court(
    sigla_tribunal: str,
    days_back: int = 7
) -> dict:
    """
    Collect intimation metadata from PJe API for a court

    Args:
        sigla_tribunal: Court code (e.g., 'TJRO', 'TJMT')
        days_back: How many days back to fetch

    Returns:
        Dictionary with statistics
    """
    logger.info("collection_start",
               tribunal=sigla_tribunal,
               days_back=days_back)

    client = PJeAPIClient()
    con = get_connection()

    try:
        # Calculate date range
        data_inicio = date.today() - timedelta(days=days_back)

        # Fetch from API
        intimations = await client.get_intimations_by_court(
            sigla_tribunal=sigla_tribunal,
            data_inicio=data_inicio
        )

        # Store intimations
        new_count = store_intimations(con, intimations)

        # Store lawyer associations
        lawyers_stored = 0
        for intimation in intimations:
            count = store_lawyer_associations(
                con,
                intimation.id,
                intimation.destinatarioadvogados
            )
            lawyers_stored += count

        logger.info("collection_complete",
                   tribunal=sigla_tribunal,
                   intimations_fetched=len(intimations),
                   intimations_new=new_count,
                   lawyers_stored=lawyers_stored)

        return {
            'tribunal': sigla_tribunal,
            'intimations_fetched': len(intimations),
            'intimations_new': new_count,
            'lawyers_stored': lawyers_stored,
            'status': 'success'
        }

    except Exception as e:
        logger.error("collection_failed",
                    tribunal=sigla_tribunal,
                    error=str(e))
        return {
            'tribunal': sigla_tribunal,
            'status': 'failed',
            'error': str(e)
        }

    finally:
        await client.close()

async def collect_metadata_for_all_courts(
    courts: List[str],
    days_back: int = 7
) -> List[dict]:
    """
    Collect metadata for multiple courts concurrently

    Args:
        courts: List of court codes
        days_back: How many days back to fetch

    Returns:
        List of result dictionaries
    """
    logger.info("multi_court_collection_start",
               courts=courts,
               count=len(courts))

    tasks = [
        collect_metadata_for_court(court, days_back)
        for court in courts
    ]

    results = await asyncio.gather(*tasks)

    successful = sum(1 for r in results if r['status'] == 'success')
    failed = sum(1 for r in results if r['status'] == 'failed')

    logger.info("multi_court_collection_complete",
               total=len(courts),
               successful=successful,
               failed=failed)

    return results

# CLI entry point
async def main():
    """CLI entry point for metadata collection"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m causaganha.v2.pipeline.collect TJRO [TJMT ...]")
        sys.exit(1)

    courts = sys.argv[1:]
    results = await collect_metadata_for_all_courts(courts)

    print("\nResults:")
    for result in results:
        print(f"  {result['tribunal']}: {result['status']}")
        if result['status'] == 'success':
            print(f"    Fetched: {result['intimations_fetched']}")
            print(f"    New: {result['intimations_new']}")

if __name__ == "__main__":
    asyncio.run(main())
```

**File**: `src/causaganha/v2/pipeline/analyze.py`

```python
"""PDF analysis pipeline"""

import asyncio
import structlog
from typing import List

from ..analysis.analyzer import DecisionAnalyzer
from ..storage.connection import get_connection
from ..storage.queries import get_unanalyzed_intimations

logger = structlog.get_logger()

async def analyze_pending_decisions(
    batch_size: int = 10,
    max_batches: int = None
) -> dict:
    """
    Analyze pending decision PDFs

    Args:
        batch_size: Number of PDFs to process at once
        max_batches: Maximum number of batches to process (None = all)

    Returns:
        Dictionary with statistics
    """
    logger.info("analysis_start",
               batch_size=batch_size,
               max_batches=max_batches)

    con = get_connection()
    analyzer = DecisionAnalyzer()

    total_analyzed = 0
    total_failed = 0
    batches_processed = 0

    while True:
        # Check batch limit
        if max_batches and batches_processed >= max_batches:
            logger.info("batch_limit_reached", batches=batches_processed)
            break

        # Get pending intimations
        pending = get_unanalyzed_intimations(con, limit=batch_size)

        if not pending:
            logger.info("no_pending_intimations")
            break

        logger.info("processing_batch",
                   batch=batches_processed + 1,
                   size=len(pending))

        # Extract URLs and IDs
        pdf_urls = [p['link'] for p in pending]
        intimation_ids = [p['id'] for p in pending]

        # Analyze batch
        try:
            analyses = await analyzer.analyze_batch(pdf_urls, intimation_ids)

            # Store results
            for analysis, intimation_id in zip(analyses, intimation_ids):
                try:
                    _store_analysis(con, intimation_id, analysis)
                    _mark_as_analyzed(con, intimation_id, success=True)
                    total_analyzed += 1
                except Exception as e:
                    logger.error("store_failed",
                                intimation_id=intimation_id,
                                error=str(e))
                    _mark_as_analyzed(con, intimation_id, success=False, error=str(e))
                    total_failed += 1

        except Exception as e:
            logger.error("batch_failed", error=str(e))
            # Mark all as failed
            for intimation_id in intimation_ids:
                _mark_as_analyzed(con, intimation_id, success=False, error=str(e))
            total_failed += len(intimation_ids)

        batches_processed += 1

    logger.info("analysis_complete",
               batches=batches_processed,
               analyzed=total_analyzed,
               failed=total_failed)

    return {
        'batches_processed': batches_processed,
        'analyzed': total_analyzed,
        'failed': total_failed,
        'status': 'success'
    }

def _store_analysis(con, intimation_id: int, analysis):
    """Store analysis results"""

    con.raw_sql(f"""
        INSERT INTO decision_analysis (
            intimation_id,
            winner_lawyer_oab, winner_lawyer_state, winner_party_name,
            loser_lawyer_oab, loser_lawyer_state, loser_party_name,
            decision_type, outcome, judge_name,
            decision_reasoning, confidence_score,
            model_used, model_provider
        ) VALUES (
            {intimation_id},
            '{analysis.winner_lawyer_oab}',
            '{analysis.winner_lawyer_state}',
            '{analysis.winner_party_name.replace("'", "''")}',
            '{analysis.loser_lawyer_oab}',
            '{analysis.loser_lawyer_state}',
            '{analysis.loser_party_name.replace("'", "''")}',
            '{analysis.decision_type}',
            '{analysis.outcome}',
            '{analysis.judge_name.replace("'", "''")}',
            '{analysis.decision_reasoning.replace("'", "''")}',
            {analysis.confidence_score},
            'gemini-2.5-flash',
            'google'
        )
        ON CONFLICT (intimation_id) DO UPDATE SET
            winner_lawyer_oab = EXCLUDED.winner_lawyer_oab,
            winner_lawyer_state = EXCLUDED.winner_lawyer_state,
            confidence_score = EXCLUDED.confidence_score
    """)

def _mark_as_analyzed(con, intimation_id: int, success: bool, error: str = None):
    """Mark intimation as analyzed"""

    con.raw_sql(f"""
        UPDATE intimations
        SET
            analyzed = {success},
            analyzed_at = {'CURRENT_TIMESTAMP' if success else 'NULL'},
            analysis_attempted_at = CURRENT_TIMESTAMP,
            analysis_error = {f"'{error.replace("'", "''")}'" if error else 'NULL'}
        WHERE id = {intimation_id}
    """)

# CLI entry point
async def main():
    """CLI entry point for PDF analysis"""
    import sys

    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    max_batches = int(sys.argv[2]) if len(sys.argv) > 2 else None

    result = await analyze_pending_decisions(batch_size, max_batches)

    print(f"\nAnalysis complete:")
    print(f"  Analyzed: {result['analyzed']}")
    print(f"  Failed: {result['failed']}")
    print(f"  Batches: {result['batches_processed']}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Migration Strategy

### Phase 1: Parallel Development (Weeks 1-3)

**Goal**: Build v2 alongside v1 without disruption

**Tasks**:
1. Create `v2/` directory structure
2. Install new dependencies (Pydantic AI, Ibis, httpx)
3. Implement core components:
   - PJe API client
   - Ibis storage layer
   - Pydantic AI analyzer
4. Write tests for each component
5. Create new database tables (don't touch existing)

**Deliverable**: Working v2 components, tested independently

### Phase 2: Integration Testing (Week 4)

**Goal**: Test v2 with real data

**Tasks**:
1. Create test script to collect data for one court (TJRO)
2. Run metadata collection → storage pipeline
3. Run PDF analysis → rating calculation pipeline
4. Compare results with v1
5. Validate data quality

**Deliverable**: Confidence that v2 produces accurate results

### Phase 3: Gradual Rollout (Weeks 5-6)

**Goal**: Switch production to v2

**Approach**:
1. Week 5: Run both v1 and v2 in parallel
   - v1 continues as normal
   - v2 collects data but doesn't publish
   - Compare outputs daily
2. Week 6: Switch to v2 primary
   - v2 becomes production system
   - v1 kept as backup for 2 weeks
   - Monitor closely

**Rollback Plan**: If issues detected, revert to v1 (keep v1 code for 1 month)

### Phase 4: Expansion (Weeks 7-8)

**Goal**: Add new courts

**Tasks**:
1. Add TJMT to monitored courts
2. Test with multiple tribunals
3. Validate cross-court rankings
4. Add more courts progressively

**Deliverable**: National coverage

### Phase 5: Cleanup (Week 9)

**Goal**: Remove legacy code

**Tasks**:
1. Archive v1 code to separate branch
2. Remove unused dependencies (pandas, scrapy, etc.)
3. Update documentation
4. Clean up GitHub Actions workflows

**Deliverable**: Clean codebase, v2 only

### Migration Timeline

```
Week 1-3: Build v2 (parallel to v1)
Week 4: Integration testing
Week 5: Parallel production run
Week 6: Switch to v2 primary
Week 7-8: Add new courts
Week 9: Cleanup
```

---

## Development Methodology

### Test-Driven Development (TDD)

**CausaGanha v2 will be built using strict TDD:**

#### TDD Workflow

```
1. Write a failing test (RED)
   ↓
2. Write minimal code to pass (GREEN)
   ↓
3. Refactor while keeping tests green (REFACTOR)
   ↓
4. Repeat
```

#### TDD Principles for This Project

**Rule 1: No production code without a failing test first**
- Write the test before the implementation
- The test must fail initially (proves it's testing something)
- Only then write code to make it pass

**Rule 2: Write the simplest test first**
- Start with happy path
- Add edge cases incrementally
- Each test should test one thing

**Rule 3: Write only enough code to pass the test**
- Don't over-engineer
- Don't add features "just in case"
- Let tests drive the design

#### Example TDD Session

```python
# Step 1: Write failing test
# tests/v2/test_api_client.py

import pytest
from causaganha.v2.api.client import PJeAPIClient

@pytest.mark.asyncio
async def test_client_initialization():
    """Test that client initializes with correct defaults"""
    client = PJeAPIClient()

    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert client.client is not None

    await client.close()

# Run test → FAILS (PJeAPIClient doesn't exist)

# Step 2: Write minimal implementation
# src/causaganha/v2/api/client.py

import httpx

class PJeAPIClient:
    def __init__(self, base_url: str = "https://comunicaapi.pje.jus.br/api/v1"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def close(self):
        await self.client.aclose()

# Run test → PASSES

# Step 3: Write next test (fetching intimations)
@pytest.mark.asyncio
async def test_fetch_intimations_returns_list():
    """Test that fetching returns a list"""
    client = PJeAPIClient()

    intimations = await client.get_intimations_by_court("TJRO")

    assert isinstance(intimations, list)
    await client.close()

# Run test → FAILS (get_intimations_by_court doesn't exist)

# Step 4: Implement get_intimations_by_court
# ... and so on
```

#### TDD Benefits for CausaGanha

1. **Confidence in refactoring**: Tests prove nothing broke
2. **Living documentation**: Tests show how to use the code
3. **Better design**: TDD forces thinking about interfaces first
4. **Fewer bugs**: Issues caught immediately
5. **Easier debugging**: Know exactly what broke

#### Testing Pyramid

```
         /\
        /  \
       / E2E \      ← Few (slow, expensive)
      /───────\
     /  Integ. \    ← Some (medium speed)
    /───────────\
   /    Unit     \  ← Many (fast, cheap)
  /_______________\
```

**Our distribution:**
- 70% Unit tests (fast, isolated)
- 20% Integration tests (pipeline stages)
- 10% E2E tests (full workflow)

---

## Development Environment Setup

### Package Management with `uv`

**CausaGanha v2 uses `uv` for fast, reliable dependency management.**

#### Why `uv`?

- ✅ 10-100x faster than pip
- ✅ Deterministic installs (lockfile)
- ✅ Built-in virtual environment management
- ✅ Compatible with pip/pyproject.toml
- ✅ No separate venv tool needed

#### Installation

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

#### Project Setup

```bash
# Clone repository
git clone https://github.com/franklinbaldo/causaganha.git
cd causaganha

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies (including dev)
uv pip install -e ".[dev]"

# Or sync from lockfile (deterministic)
uv pip sync requirements.txt
```

#### Common `uv` Commands

```bash
# Add a new dependency
uv pip install pydantic-ai
uv pip freeze > requirements.txt

# Install dev dependencies
uv pip install -e ".[dev,test]"

# Run commands in the venv (without activation)
uv run pytest
uv run python -m causaganha.v2.pipeline.collect TJRO

# Update dependencies
uv pip install --upgrade pydantic-ai

# Compile requirements from pyproject.toml
uv pip compile pyproject.toml -o requirements.txt
```

#### Updated `pyproject.toml`

```toml
[project]
name = "causaganha"
version = "2.0.0-alpha"
description = "Judicial analytics platform with OpenSkill ratings"
authors = [{name = "Franklin Silveira Baldo", email = "franklin@example.com"}]
requires-python = ">=3.11"
dependencies = [
    "pydantic-ai>=0.0.14",
    "ibis-framework[duckdb]>=9.0",
    "httpx>=0.27",
    "pydantic>=2.10",
    "google-generativeai>=0.3",
    "python-dotenv>=1.0",
    "structlog>=24.1",
    "rich>=13.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.1",
    "ruff>=0.8",
    "mypy>=1.8",
]

test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.12",
    "httpx[testing]>=0.27",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = """
    -v
    --strict-markers
    --cov=causaganha
    --cov-report=html
    --cov-report=term-missing
"""

[tool.coverage.run]
source = ["src/causaganha"]
omit = ["*/tests/*", "*/legacy/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

### Code Quality with Ruff

**CausaGanha v2 uses Ruff for linting and formatting with ZERO exceptions.**

#### Ruff Configuration

**File**: `ruff.toml`

```toml
# Ruff configuration for CausaGanha v2
# Strict mode: ALL rules enabled, NO exceptions

# Target Python 3.11+
target-version = "py311"

# Line length
line-length = 100

# Enable ALL Ruff rules
select = ["ALL"]

# NO EXCEPTIONS - Do not ignore any rules
# If Ruff complains, fix the code, don't silence it
ignore = []

# NO per-file ignores either
# Every file must pass all rules
[per-file-ignores]
# Empty - no exceptions

[mccabe]
# Maximum cyclomatic complexity
max-complexity = 10

[pydocstyle]
# Use Google docstring convention
convention = "google"

[isort]
# Import sorting
known-first-party = ["causaganha"]
force-single-line = false
lines-after-imports = 2

[flake8-quotes]
inline-quotes = "double"
multiline-quotes = "double"
docstring-quotes = "double"

[pylint]
max-args = 5
max-branches = 12
max-returns = 6
max-statements = 50

[format]
# Formatting options
quote-style = "double"
indent-style = "space"
line-ending = "auto"
```

#### Strict Rules Enforcement

**Rule 1: NO `# noqa` comments allowed**

```python
# ❌ FORBIDDEN - Will be rejected in PR review
import os  # noqa: F401

# ✅ CORRECT - Remove unused import
# (don't import if not used)
```

**Rule 2: NO `# type: ignore` comments allowed**

```python
# ❌ FORBIDDEN
result = some_function()  # type: ignore[attr-defined]

# ✅ CORRECT - Fix the type issue
result: SomeType = some_function()
# or properly type-hint the function
```

**Rule 3: NO `# pragma: no cover` in production code**

```python
# ❌ FORBIDDEN in src/
def some_function():
    if edge_case:  # pragma: no cover
        handle_edge_case()

# ✅ CORRECT - Write a test for it
def test_edge_case():
    """Test that edge case is handled"""
    result = some_function()
    assert result.handles_edge_case
```

#### Pre-commit Hook

**File**: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      # Run Ruff linter
      - id: ruff
        args: [--fix]
        types_or: [python, pyi]
      # Run Ruff formatter
      - id: ruff-format
        types_or: [python, pyi]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml
      - id: check-added-large-files
        args: ['--maxkb=1000']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic>=2.0]
        args: [--strict]
```

#### Setup Pre-commit

```bash
# Install pre-commit hooks
uv pip install pre-commit
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Or just run Ruff
uv run ruff check .
uv run ruff format .
```

#### Development Workflow with Ruff

```bash
# Before writing code, make sure Ruff is happy with existing code
uv run ruff check src/causaganha/v2/

# Write your test (TDD)
vim tests/v2/test_api_client.py

# Write implementation
vim src/causaganha/v2/api/client.py

# Format and check continuously
uv run ruff format src/causaganha/v2/api/client.py
uv run ruff check src/causaganha/v2/api/client.py

# Fix any issues (don't ignore!)
# Ruff will show exactly what to fix

# Run tests
uv run pytest tests/v2/test_api_client.py

# Commit (pre-commit will run Ruff automatically)
git add .
git commit -m "feat: implement PJe API client"
```

#### Handling Ruff Errors

**When Ruff complains, you have 3 options:**

1. ✅ **Fix the code** (preferred)
2. ✅ **Refactor to avoid the issue** (also good)
3. ❌ **Ignore with noqa** (FORBIDDEN)

**Examples:**

```python
# Ruff: "Function is too complex (C901)"
# ❌ Don't ignore
def complex_function():  # noqa: C901
    # 50 lines of complex logic
    pass

# ✅ Refactor into smaller functions
def complex_function():
    _validate_input()
    _process_data()
    _format_output()

# Ruff: "Line too long (E501)"
# ❌ Don't ignore
some_very_long_function_call(param1, param2, param3, param4, param5)  # noqa: E501

# ✅ Break into multiple lines
some_very_long_function_call(
    param1,
    param2,
    param3,
    param4,
    param5,
)

# Ruff: "Unused variable (F841)"
# ❌ Don't ignore
result = fetch_data()  # noqa: F841
process()

# ✅ Use the variable or remove it
result = fetch_data()
process(result)
# or
fetch_data()  # Call for side effects only
process()
```

#### CI/CD Integration

**GitHub Actions workflow includes Ruff:**

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          uv venv
          uv pip install -e ".[dev]"
      - name: Run Ruff (linting)
        run: uv run ruff check . --no-fix
      - name: Run Ruff (formatting check)
        run: uv run ruff format --check .
      - name: Run mypy
        run: uv run mypy src/causaganha/v2

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          uv venv
          uv pip install -e ".[dev,test]"
      - name: Run tests
        run: uv run pytest --cov
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

#### Code Review Checklist

Every PR must pass:
- ✅ All tests pass (`uv run pytest`)
- ✅ Ruff linting passes (`uv run ruff check .`)
- ✅ Ruff formatting passes (`uv run ruff format --check .`)
- ✅ Type checking passes (`uv run mypy src/causaganha/v2`)
- ✅ Coverage >= 80% (`uv run pytest --cov`)
- ✅ NO `noqa` comments
- ✅ NO `type: ignore` comments
- ✅ NO `pragma: no cover` (except in tests/)

---

## Testing Approach

### Test-Driven Development in Practice

**Every feature follows this TDD cycle:**

1. **Write test first** (test_feature.py)
2. **Run test** → RED (fails)
3. **Write minimal code** → GREEN (passes)
4. **Refactor** → Keep GREEN
5. **Repeat** for next test

### Unit Tests (TDD)

**Write tests BEFORE implementation:**

#### Example TDD Session: API Client

```python
# tests/v2/test_api_client.py
"""
TDD Example: Building the PJe API Client
Each test is written before the implementation
"""

import pytest
from causaganha.v2.api.client import PJeAPIClient

# TEST 1: Client initialization
@pytest.mark.asyncio
async def test_client_initializes_with_defaults():
    """
    RED → GREEN → REFACTOR

    This test is written FIRST, before PJeAPIClient exists
    """
    client = PJeAPIClient()

    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert client.client is not None

    await client.close()

# Now implement PJeAPIClient to make test pass (minimal code)

# TEST 2: Fetching returns list
@pytest.mark.asyncio
async def test_fetch_intimations_returns_list():
    """
    Next test: Method should return a list
    Write this BEFORE implementing get_intimations_by_court
    """
    client = PJeAPIClient()

    intimations = await client.get_intimations_by_court("TJRO")

    assert isinstance(intimations, list)
    await client.close()

# Now implement get_intimations_by_court (just enough to return empty list)

# TEST 3: Pagination works
@pytest.mark.asyncio
async def test_fetch_handles_pagination():
    """
    Test pagination BEFORE implementing it
    """
    client = PJeAPIClient()

    # Mock API to return multiple pages
    # ... implementation of mock

    intimations = await client.get_intimations_by_court("TJRO")

    # Should have fetched from multiple pages
    assert len(intimations) > 100  # More than one page

    await client.close()

# Now implement pagination logic

# TEST 4: Error handling
@pytest.mark.asyncio
async def test_fetch_raises_on_http_error():
    """
    Test error handling BEFORE implementing it
    """
    client = PJeAPIClient()

    with pytest.raises(httpx.HTTPError):
        # Force an HTTP error
        await client.get_intimations_by_court("INVALID")

    await client.close()

# Now add proper error handling
```

#### TDD Benefits Demonstrated

**Test 1 → Implementation:**
```python
# Minimal implementation to pass test
class PJeAPIClient:
    def __init__(self, base_url: str = "https://comunicaapi.pje.jus.br/api/v1"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def close(self):
        await self.client.aclose()
```

**Test 2 → Implementation:**
```python
# Add just enough to return empty list
class PJeAPIClient:
    # ... existing code ...

    async def get_intimations_by_court(self, sigla_tribunal: str) -> list:
        return []  # Simplest implementation that passes
```

**Test 3 → Implementation:**
```python
# Now add real pagination logic
async def get_intimations_by_court(self, sigla_tribunal: str) -> list:
    all_intimations = []
    offset = 0
    limit = 100

    while True:
        params = {"siglaTribunal": sigla_tribunal, "offset": offset, "limit": limit}
        response = await self.client.get(f"{self.base_url}/comunicacao", params=params)
        data = response.json()

        items = data.get("items", [])
        if not items:
            break

        all_intimations.extend(items)
        offset += limit

        if len(all_intimations) >= data.get("count", 0):
            break

    return all_intimations
```

### Test Organization

```
tests/
├── v2/
│   ├── conftest.py              # Shared fixtures
│   │
│   ├── unit/                    # Fast, isolated tests
│   │   ├── test_api_client.py
│   │   ├── test_storage.py
│   │   ├── test_analyzer.py
│   │   └── test_models.py
│   │
│   ├── integration/             # Component integration
│   │   ├── test_api_to_storage.py
│   │   ├── test_storage_to_analysis.py
│   │   └── test_analysis_to_ratings.py
│   │
│   └── e2e/                     # Full pipeline tests
│       ├── test_full_pipeline.py
│       └── test_multi_court.py
│
└── fixtures/                    # Test data
    ├── sample_intimations.json
    ├── sample_pdf.pdf
    └── mock_api_responses.json
```

### Test Coverage Requirements

**Strict coverage rules:**
- Minimum 80% overall coverage
- 100% coverage for critical paths:
  - API client (all methods)
  - Decision analyzer (all outcomes)
  - OpenSkill calculations
- NO `pragma: no cover` except in test files themselves

```bash
# Generate coverage report
uv run pytest --cov=causaganha/v2 --cov-report=html --cov-report=term

# View in browser
open htmlcov/index.html

# Fail CI if coverage drops below 80%
uv run pytest --cov=causaganha/v2 --cov-fail-under=80
```

### Test Fixtures

```python
# tests/v2/conftest.py
"""
Shared test fixtures following TDD principles
Fixtures are written as tests are written
"""

import pytest
from causaganha.v2.api.client import PJeAPIClient
from causaganha.v2.storage.connection import get_connection
from causaganha.v2.analysis.analyzer import DecisionAnalyzer

@pytest.fixture
async def api_client():
    """Provide a clean API client for tests"""
    client = PJeAPIClient()
    yield client
    await client.close()

@pytest.fixture
def db_connection():
    """Provide an in-memory database for tests"""
    con = get_connection(":memory:")
    yield con
    # Connection closed automatically with DuckDB

@pytest.fixture
def analyzer():
    """Provide a decision analyzer for tests"""
    return DecisionAnalyzer(model_name="gemini-2.5-flash")

@pytest.fixture
def sample_intimation():
    """Sample intimation data for testing"""
    return {
        "id": 123456,
        "numero_processo": "0001234-56.2024.8.22.0001",
        "siglaTribunal": "TJRO",
        "data_disponibilizacao": "2024-12-01",
        "link": "https://example.com/doc.pdf",
        "hash": "abc123",
        "destinatarioadvogados": [
            {
                "advogado": {
                    "id": 1,
                    "nome": "FRANKLIN SILVEIRA BALDO",
                    "numero_oab": "5733",
                    "uf_oab": "RO"
                }
            }
        ]
    }

@pytest.fixture
def sample_decision_analysis():
    """Sample decision analysis for testing"""
    from causaganha.v2.analysis.models import DecisionAnalysis

    return DecisionAnalysis(
        winner_lawyer_oab="5733",
        winner_lawyer_state="RO",
        winner_party_name="João da Silva",
        loser_lawyer_oab="6789",
        loser_lawyer_state="RO",
        loser_party_name="Maria Souza",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Dr. José Santos",
        decision_reasoning="Pedido procedente com base no art. 123.",
        confidence_score=0.95
    )
```

### Mocking External Dependencies

```python
# tests/v2/unit/test_api_client.py
"""
Unit tests should mock external dependencies
Test the logic, not the network
"""

import pytest
from unittest.mock import AsyncMock, patch
from causaganha.v2.api.client import PJeAPIClient

@pytest.mark.asyncio
async def test_fetch_intimations_success(api_client):
    """
    Test API fetch with mocked HTTP response
    Written BEFORE implementation
    """
    mock_response = {
        "status": "success",
        "count": 1,
        "items": [
            {
                "id": 123,
                "numero_processo": "0001234-56.2024.8.22.0001",
                "siglaTribunal": "TJRO",
                # ... rest of fields
            }
        ]
    }

    with patch.object(api_client.client, 'get') as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = lambda: None

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert len(intimations) == 1
        assert intimations[0].id == 123

@pytest.mark.asyncio
async def test_fetch_intimations_http_error(api_client):
    """
    Test error handling with mocked HTTP error
    Written BEFORE implementation
    """
    import httpx

    with patch.object(api_client.client, 'get') as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network error")

        with pytest.raises(httpx.HTTPError):
            await api_client.get_intimations_by_court("TJRO")
```

### Property-Based Testing

For complex logic, use property-based testing:

```python
# tests/v2/unit/test_rating_calculation.py
"""
Property-based testing for OpenSkill calculations
Tests mathematical properties rather than specific examples
"""

from hypothesis import given, strategies as st
from causaganha.scoring.openskill import rate

@given(
    winner_mu=st.floats(min_value=0, max_value=50),
    winner_sigma=st.floats(min_value=1, max_value=10),
    loser_mu=st.floats(min_value=0, max_value=50),
    loser_sigma=st.floats(min_value=1, max_value=10),
)
def test_winner_rating_increases(winner_mu, winner_sigma, loser_mu, loser_sigma):
    """
    Property: Winner's rating should always increase
    Test with random inputs
    """
    winner_before = (winner_mu, winner_sigma)
    loser_before = (loser_mu, loser_sigma)

    winner_after, loser_after = rate([winner_before], [loser_before])

    # Winner's mu should increase
    assert winner_after[0] >= winner_mu

    # Loser's mu should decrease
    assert loser_after[0] <= loser_mu
```

### Unit Tests

```python
# tests/v2/test_api_client.py
import pytest
from causaganha.v2.api.client import PJeAPIClient

@pytest.mark.asyncio
async def test_fetch_intimations():
    """Test API client can fetch intimations"""
    client = PJeAPIClient()

    intimations = await client.get_intimations_by_court(
        sigla_tribunal="TJRO",
        days_back=1
    )

    assert len(intimations) > 0
    assert intimations[0].id is not None
    await client.close()

# tests/v2/test_analyzer.py
import pytest
from causaganha.v2.analysis.analyzer import DecisionAnalyzer

@pytest.mark.asyncio
async def test_analyze_pdf():
    """Test PDF analysis"""
    analyzer = DecisionAnalyzer()

    # Use a test PDF URL
    result = await analyzer.analyze_pdf(
        pdf_url="https://example.com/test.pdf"
    )

    assert result.winner_lawyer_oab is not None
    assert 0 <= result.confidence_score <= 1

# tests/v2/test_storage.py
import pytest
from causaganha.v2.storage.connection import get_connection
from causaganha.v2.storage.queries import store_intimations

def test_store_intimations():
    """Test storing intimations"""
    con = get_connection(":memory:")  # In-memory for testing

    # Mock intimation data
    intimations = [...]

    count = store_intimations(con, intimations)
    assert count > 0
```

### Integration Tests

**Test full pipeline:**

```python
# tests/v2/test_integration.py
import pytest
from causaganha.v2.pipeline.collect import collect_metadata_for_court
from causaganha.v2.pipeline.analyze import analyze_pending_decisions

@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_pipeline():
    """Test complete pipeline from API to ratings"""

    # 1. Collect metadata
    result = await collect_metadata_for_court("TJRO", days_back=1)
    assert result['status'] == 'success'
    assert result['intimations_fetched'] > 0

    # 2. Analyze decisions
    analysis_result = await analyze_pending_decisions(batch_size=5, max_batches=1)
    assert analysis_result['analyzed'] > 0

    # 3. Check database
    con = get_connection()
    intimations = con.table('intimations')
    count = intimations.count().execute()
    assert count > 0
```

### Validation Tests

**Compare v1 vs v2 outputs:**

```python
# tests/v2/test_validation.py
def test_rating_consistency():
    """Compare ratings between v1 and v2"""

    # Get ratings from v1 database
    v1_ratings = get_v1_ratings()

    # Get ratings from v2 database
    v2_ratings = get_v2_ratings()

    # Compare (allowing for small differences due to ordering)
    for lawyer_id in v1_ratings:
        v1_rating = v1_ratings[lawyer_id]
        v2_rating = v2_ratings.get(lawyer_id)

        if v2_rating:
            # Ratings should be within 5% (due to minor differences in data)
            diff_pct = abs(v1_rating - v2_rating) / v1_rating
            assert diff_pct < 0.05, f"Large difference for {lawyer_id}"
```

---

## Timeline

### Detailed Schedule

| Week | Focus | Tasks | Deliverables | TDD/Quality Gates |
|------|-------|-------|--------------|-------------------|
| **1** | Setup | - Install uv<br>- Setup ruff.toml<br>- Configure pre-commit<br>- Create v2 structure<br>- Setup pytest | Working dev environment | - All Ruff rules pass<br>- Pre-commit hooks installed<br>- CI pipeline configured |
| **2** | API & Storage (TDD) | - Write API client tests FIRST<br>- Implement API client<br>- Write storage tests FIRST<br>- Implement Ibis storage<br>- All code passes Ruff | API client + storage layer | - 100% test coverage for API<br>- 100% coverage for storage<br>- Zero Ruff violations |
| **3** | Analysis (TDD) | - Write analyzer tests FIRST<br>- Implement Pydantic AI analyzer<br>- Test with sample PDFs<br>- Tune prompts iteratively | Working analyzer | - 90% coverage for analyzer<br>- Integration tests pass<br>- No noqa comments |
| **4** | Integration | - Write pipeline tests FIRST<br>- Build pipelines<br>- Integration testing<br>- Fix bugs with tests | End-to-end pipeline | - 80% overall coverage<br>- All integration tests pass<br>- Ruff + mypy clean |
| **5** | Parallel Run | - Run v1 + v2 together<br>- Compare outputs<br>- Monitor quality<br>- Add regression tests | Production validation | - Regression test suite<br>- Performance benchmarks<br>- Data quality validation |
| **6** | Switchover | - Make v2 primary<br>- Monitor closely<br>- Keep v1 as backup | v2 in production | - All tests green<br>- Coverage maintained<br>- Zero Ruff violations |
| **7-8** | Expansion | - TDD new court adapters<br>- Add TJMT, more courts<br>- Test cross-court | Multi-court coverage | - Tests for each court<br>- Coverage ≥ 80%<br>- Clean code (Ruff) |
| **9** | Cleanup | - Remove v1 code<br>- Update docs<br>- Final Ruff pass | Clean codebase | - 100% Ruff compliance<br>- Updated documentation<br>- No technical debt |

### Daily Development Workflow

**Every day follows this TDD cycle:**

```
Morning:
09:00 - Pull latest changes
        uv run ruff check .
        uv run ruff format .
        uv run pytest

10:00 - RED: Write failing test for next feature
        uv run pytest tests/v2/test_new_feature.py → FAILS ✓

11:00 - GREEN: Implement minimal code
        uv run pytest tests/v2/test_new_feature.py → PASSES ✓
        uv run ruff format src/causaganha/v2/

12:00 - Lunch

Afternoon:
13:00 - REFACTOR: Improve code while keeping tests green
        uv run pytest → PASSES ✓
        uv run ruff check . → CLEAN ✓

14:00 - Add more tests (edge cases)
        RED → GREEN → REFACTOR cycle

16:00 - Review coverage
        uv run pytest --cov
        Coverage report: aim for >80%

17:00 - Commit & Push
        git add .
        git commit -m "feat: implement feature X (TDD)"
        # pre-commit runs Ruff automatically
        git push
        # CI runs all tests + Ruff + mypy
```

### Weekly Code Review Checklist

**Before merging any PR:**

```bash
# 1. All tests pass
uv run pytest -v
✅ All tests passed

# 2. Coverage is adequate
uv run pytest --cov --cov-fail-under=80
✅ Coverage: 87%

# 3. Ruff linting
uv run ruff check . --no-fix
✅ No issues found

# 4. Ruff formatting
uv run ruff format --check .
✅ All files formatted correctly

# 5. Type checking
uv run mypy src/causaganha/v2
✅ No type errors

# 6. No forbidden patterns
grep -r "noqa" src/causaganha/v2/ && echo "❌ REJECT: noqa found"
grep -r "type: ignore" src/causaganha/v2/ && echo "❌ REJECT: type: ignore found"
grep -r "pragma: no cover" src/causaganha/v2/ && echo "❌ REJECT: pragma in src/"
✅ No forbidden patterns

# 7. Manual code review
# - Is the code readable?
# - Are tests meaningful?
# - Is the design clean?
✅ Code review approved
```

### Critical Path (with TDD emphasis)

```
Week 1: Setup (Ruff, uv, pytest)
   ↓
Week 2: TDD API/Storage
   ↓ (tests written first for everything)
Week 3: TDD Analysis
   ↓ (tests guide design)
Week 4: TDD Integration
   ↓
Week 5: Validation (all tests green)
   ↓
Week 6: Production (tests give confidence)
   ↓
Week 7-8: TDD Expansion (test new courts first)
   ↓
Week 9: Cleanup (final quality pass)
```

### Quality Gates (Non-negotiable)

**These gates MUST pass before moving to next phase:**

#### Phase 1 → Phase 2
- ✅ Ruff configuration working
- ✅ Pre-commit hooks installed
- ✅ CI pipeline passing
- ✅ All developers trained on TDD

#### Phase 2 → Phase 3
- ✅ API client: 100% test coverage
- ✅ Storage layer: 100% test coverage
- ✅ Zero Ruff violations
- ✅ All tests pass in CI

#### Phase 3 → Phase 4
- ✅ Analyzer: ≥90% coverage
- ✅ Integration tests pass
- ✅ No noqa/type:ignore comments
- ✅ Ruff + mypy clean

#### Phase 4 → Phase 5
- ✅ Overall coverage ≥80%
- ✅ All integration tests pass
- ✅ Performance benchmarks met
- ✅ Zero Ruff violations

#### Phase 5 → Phase 6
- ✅ Data quality validated
- ✅ Regression tests pass
- ✅ Production monitoring ready
- ✅ All tests green

#### Phase 6 → Phase 7
- ✅ 1 week in production without issues
- ✅ All metrics green
- ✅ Test coverage maintained
- ✅ Code quality maintained

---

## Risks & Mitigation

### Risk 1: PJe API Limitations

**Risk**: API might not cover all courts or might have rate limits

**Impact**: High - affects core functionality

**Mitigation**:
- Test API coverage early (Week 1)
- Create fallback to web scraping for uncovered courts
- Implement rate limiting and backoff in client
- Cache responses aggressively

**Contingency**: Keep web scraping code for courts without API access

### Risk 2: AI Analysis Quality

**Risk**: Pydantic AI might produce incorrect win/loss determinations

**Impact**: Critical - affects rating accuracy

**Mitigation**:
- Extensive testing with known cases
- Use confidence scores to filter low-quality analyses
- Manual validation of sample (100 cases)
- A/B testing against existing v1 analyses

**Contingency**: Implement human review workflow for low-confidence cases

### Risk 3: Performance Issues

**Risk**: Ibis might not be as fast as expected, or API might be slow

**Impact**: Medium - affects processing speed

**Mitigation**:
- Benchmark early (Week 2)
- Optimize queries with proper indexes
- Use connection pooling
- Implement caching

**Contingency**: Revert to Pandas if Ibis doesn't perform, or increase parallelization

### Risk 4: Data Migration Problems

**Risk**: Historical v1 data might not map cleanly to v2 schema

**Impact**: Medium - affects continuity

**Mitigation**:
- Design schema with backwards compatibility
- Create migration script early
- Test migration with subset of data
- Keep v1 database intact during transition

**Contingency**: Run v1 and v2 in parallel longer if needed

### Risk 5: API Changes or Downtime

**Risk**: PJe API might change or go offline

**Impact**: High - blocks all data collection

**Mitigation**:
- Monitor API health
- Implement retry logic with exponential backoff
- Cache API responses locally
- Have alerting for API failures

**Contingency**: Fall back to web scraping temporarily

---

## Success Metrics

### Technical Metrics

1. **Data Coverage**
   - Target: 95% of intimations captured from monitored courts
   - Measure: Compare API results against official court statistics

2. **Analysis Accuracy**
   - Target: 90% accuracy on win/loss determination
   - Measure: Manual validation of 100 random cases

3. **Performance**
   - Target: Process 1000 intimations in <30 minutes
   - Measure: Pipeline execution time

4. **Reliability**
   - Target: 99% uptime for data collection
   - Measure: Failed sync attempts / total attempts

5. **Cost Efficiency**
   - Target: <50% of current LLM costs
   - Measure: API calls before/after (metadata extraction no longer needed)

### Business Metrics

1. **Court Coverage**
   - Target: 10+ courts by end of Q1 2025
   - Current: 1 court (TJRO)

2. **Data Quality**
   - Target: <2% error rate in lawyer-case associations
   - Current: ~5% error rate (from text extraction)

3. **Ranking Completeness**
   - Target: Rankings for 10,000+ lawyers
   - Current: ~2,000 lawyers (TJRO only)

4. **Publication Frequency**
   - Target: Daily updates
   - Current: Weekly updates

### User Metrics

1. **Transparency**
   - All data and methodology published
   - Database accessible via Internet Archive
   - Reproducible results

2. **Accessibility**
   - DuckDB file downloadable
   - Clear documentation
   - Query examples provided

---

## Code Quality Standards

### The Non-Negotiables

**CausaGanha v2 enforces strict code quality standards:**

1. **Test-Driven Development (TDD)**
   - Tests written before implementation
   - No code without tests
   - Coverage ≥80% overall, 100% for critical paths

2. **Ruff Compliance**
   - ALL rules enabled
   - Zero violations allowed
   - NO exceptions (noqa, type:ignore, pragma)

3. **Type Safety**
   - Full type hints on all functions
   - mypy in strict mode
   - No `Any` types in public APIs

4. **Documentation**
   - Google-style docstrings for all public functions
   - Type hints serve as inline documentation
   - Examples in docstrings where helpful

### Code Review Standards

**Every PR must:**
- ✅ Have tests (written first, via TDD)
- ✅ Pass all existing tests
- ✅ Pass Ruff (linting + formatting)
- ✅ Pass mypy (type checking)
- ✅ Maintain or improve coverage
- ✅ Have clear commit messages
- ✅ Have NO noqa/type:ignore/pragma comments

**Reviewers check for:**
- Are tests meaningful (not just for coverage)?
- Is the code readable?
- Are variable names descriptive?
- Is the design simple?
- Could this be refactored for clarity?

### Example of High-Quality Code

```python
"""
Example: High-quality code following all standards
- TDD (tests written first)
- Ruff compliant (all rules)
- Fully type-hinted
- Well documented
"""

from typing import Protocol
from pydantic import BaseModel


class Intimation(BaseModel):
    """
    Represents a judicial intimation from PJe API.

    Attributes:
        id: Unique intimation identifier
        numero_processo: Process number in format NNNNNNN-DD.YYYY.J.TT.OOOO
        sigla_tribunal: Court code (e.g., 'TJRO', 'TJMT')

    Example:
        >>> intimation = Intimation(
        ...     id=123456,
        ...     numero_processo="0001234-56.2024.8.22.0001",
        ...     sigla_tribunal="TJRO"
        ... )
        >>> intimation.sigla_tribunal
        'TJRO'
    """

    id: int
    numero_processo: str
    sigla_tribunal: str


class StorageProtocol(Protocol):
    """Protocol defining storage interface."""

    def store_intimation(self, intimation: Intimation) -> bool:
        """
        Store an intimation.

        Args:
            intimation: The intimation to store

        Returns:
            True if stored successfully, False otherwise
        """
        ...


def process_intimations(
    intimations: list[Intimation],
    storage: StorageProtocol,
) -> tuple[int, int]:
    """
    Process a batch of intimations.

    This function stores intimations and returns statistics.
    Follows single responsibility principle - only handles storage,
    not validation or transformation.

    Args:
        intimations: List of intimations to process
        storage: Storage implementation to use

    Returns:
        Tuple of (successful_count, failed_count)

    Example:
        >>> intimations = [Intimation(...), Intimation(...)]
        >>> storage = DuckDBStorage()
        >>> succeeded, failed = process_intimations(intimations, storage)
        >>> print(f"Processed {succeeded} successfully")
    """
    succeeded = 0
    failed = 0

    for intimation in intimations:
        if storage.store_intimation(intimation):
            succeeded += 1
        else:
            failed += 1

    return succeeded, failed


# Tests written FIRST (TDD)
# tests/test_processor.py

import pytest
from unittest.mock import Mock


def test_process_intimations_success():
    """Test processing intimations successfully (written first)."""
    # Arrange
    intimations = [
        Intimation(id=1, numero_processo="0001-01.2024.8.22.0001", sigla_tribunal="TJRO"),
        Intimation(id=2, numero_processo="0002-01.2024.8.22.0001", sigla_tribunal="TJRO"),
    ]
    storage = Mock(spec=StorageProtocol)
    storage.store_intimation.return_value = True

    # Act
    succeeded, failed = process_intimations(intimations, storage)

    # Assert
    assert succeeded == 2
    assert failed == 0
    assert storage.store_intimation.call_count == 2


def test_process_intimations_partial_failure():
    """Test handling partial failures (written first)."""
    intimations = [
        Intimation(id=1, numero_processo="0001-01.2024.8.22.0001", sigla_tribunal="TJRO"),
        Intimation(id=2, numero_processo="0002-01.2024.8.22.0001", sigla_tribunal="TJRO"),
    ]
    storage = Mock(spec=StorageProtocol)
    storage.store_intimation.side_effect = [True, False]  # First succeeds, second fails

    succeeded, failed = process_intimations(intimations, storage)

    assert succeeded == 1
    assert failed == 1
```

### What Good Code Looks Like

✅ **Good:**
```python
def calculate_win_rate(wins: int, total_cases: int) -> float:
    """
    Calculate win rate as a percentage.

    Args:
        wins: Number of cases won
        total_cases: Total number of cases

    Returns:
        Win rate as float between 0.0 and 1.0

    Raises:
        ValueError: If total_cases is negative or wins > total_cases
    """
    if total_cases < 0:
        msg = f"total_cases must be non-negative, got {total_cases}"
        raise ValueError(msg)

    if wins > total_cases:
        msg = f"wins ({wins}) cannot exceed total_cases ({total_cases})"
        raise ValueError(msg)

    if total_cases == 0:
        return 0.0

    return wins / total_cases
```

❌ **Bad:**
```python
def calc(w, t):  # type: ignore[misc]  # ❌ FORBIDDEN
    """calc win rate"""  # ❌ Poor docstring
    if t == 0:  # ❌ No validation
        return 0
    return w/t  # noqa: E501  # ❌ FORBIDDEN
```

### Commit Message Standards

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `test:` Adding tests
- `refactor:` Code refactoring
- `docs:` Documentation
- `style:` Formatting (but Ruff handles this)
- `chore:` Maintenance

**Examples:**

✅ Good:
```
feat(api): implement PJe API client with pagination

- Add PJeAPIClient class with async methods
- Implement automatic pagination for large result sets
- Add comprehensive error handling
- Tests written first following TDD

Closes #123
```

✅ Good:
```
test(analyzer): add property-based tests for decision analysis

- Use hypothesis for property-based testing
- Test invariants in decision analysis
- Improve coverage from 85% to 95%
```

❌ Bad:
```
stuff  # ❌ Not descriptive
```

❌ Bad:
```
fix bug  # ❌ Which bug? What fix?
```

---

## Conclusion

This refactoring transforms CausaGanha from a single-court, scraping-based system to a **national-scale, API-driven judicial analytics platform**.

### Key Improvements

1. **Reliability**: Official API instead of fragile web scraping
2. **Scale**: 90+ courts instead of 1
3. **Quality**: Better metadata, fewer extraction errors
4. **Performance**: Ibis queries 10-100x faster than Pandas
5. **Flexibility**: Pydantic AI allows easy model switching
6. **Maintainability**: Less code, fewer dependencies

### What Doesn't Change

- OpenSkill rating algorithm (proven and working)
- Distributed architecture (DuckDB + Internet Archive)
- AI-powered decision analysis (still essential)
- Open, transparent methodology

### The Hybrid Approach

The key insight is that **the PJe API and AI analysis are complementary**:
- API provides reliable metadata
- AI extracts outcomes from PDFs
- Together, they enable accurate, scalable lawyer rankings

This refactoring makes CausaGanha more robust, scalable, and valuable as a transparency tool for the Brazilian legal system.
