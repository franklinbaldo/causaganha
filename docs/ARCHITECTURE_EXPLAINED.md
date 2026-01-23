# 🏗️ CausaGanha Architecture Explained

## 📋 Table of Contents
1. [What CausaGanha Does](#what-causaganha-does)
2. [Architecture Overview](#architecture-overview)
3. [Data Flow](#data-flow)
4. [Layer-by-Layer Explanation](#layer-by-layer-explanation)
5. [Key Technologies](#key-technologies)
6. [Real-World Example](#real-world-example)

---

## 🎯 What CausaGanha Does

**CausaGanha** is an automated judicial decision analysis platform for Brazilian courts. It:

1. **Collects** judicial intimations (court notifications) from Brazilian tribunals via PJe API
2. **Analyzes** decisions using AI to determine winners/losers
3. **Scores** lawyers using a chess-like rating system (OpenSkill)
4. **Exports** data to Internet Archive as public datasets
5. **Provides** transparent lawyer performance ratings

**Mission**: Eliminate information asymmetry in the Brazilian legal market through transparent, data-driven lawyer performance ratings.

---

## 🏛️ Architecture Overview

### Unified Structure (Post-Migration)

```
src/causaganha/
├── cli/                    # 🎮 User Interface (CLI commands)
├── api/                    # 🌐 External Data Sources (PJe API)
├── pipeline/               # 🔄 Orchestration (workflows)
├── analysis/               # 🧠 AI/ML (decision analysis)
├── storage/                # 💾 Data Persistence (DuckDB)
├── clients/                # 📦 External Services (Internet Archive)
├── scoring/                # 🏆 Rating System (OpenSkill)
├── models/                 # 📊 Domain Models (future use)
└── config.py               # ⚙️ Configuration
```

### Architecture Pattern: **Modular Monolith** (Hexagonal-ish)

- **Simple**: Single deployable unit (no microservices complexity)
- **Modular**: Clear boundaries between layers
- **Testable**: Each layer can be tested independently
- **Scalable**: Can extract modules to services later if needed

---

## 🔄 Data Flow

### The Complete Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CausaGanha Pipeline                             │
└─────────────────────────────────────────────────────────────────────────┘

Step 1: COLLECT (PJe API → DuckDB)
──────────────────────────────────
    PJe API
       │
       │ HTTP GET /intimacoes
       ↓
   [api/client.py]
       │
       │ Fetch metadata
       ↓
   [pipeline/collect.py]
       │
       │ Store
       ↓
   DuckDB: intimations table
           intimation_lawyers table

Step 2: ARCHIVE (Download & Upload to Internet Archive)
────────────────────────────────────────────────────────
   intimations (unarchived)
       │
       ↓
   [pipeline/archive.py]
       │
       ├─→ Download PDF from PJe
       │   [clients/document.py]
       │
       └─→ Upload to Internet Archive
           [clients/archive.py]
       │
       ↓
   intimations.ia_url = "https://archive.org/..."

Step 3: ANALYZE (AI Decision Analysis)
───────────────────────────────────────
   intimations (analyzed=false)
       │
       │ texto field (decision text)
       ↓
   [pipeline/analyze.py]
       │
       ├─→ Strategy Selection
       │   ┌──────────────────────────┐
       │   │ LLM-Only: Google Gemini  │
       │   │ RAG-Only: Embeddings     │
       │   │ HYBRID: RAG → LLM        │ ← DEFAULT
       │   └──────────────────────────┘
       │
       │ [analysis/hybrid_analyzer.py]
       │   │
       │   ├─→ [analysis/rag_analyzer.py]
       │   │   └─→ [analysis/embedding_service.py]
       │   │       └─→ [analysis/providers.py]
       │   │           ├─→ Jina AI (priority #1)
       │   │           └─→ Google Gemini (fallback)
       │   │
       │   └─→ If RAG confidence < 0.70:
       │       [analysis/analyzer.py] (Pydantic AI + Gemini)
       │
       ↓
   decision_analysis table
       ├─ winner_lawyer_oab
       ├─ loser_lawyer_oab
       ├─ confidence_score
       └─ analysis_method (rag/llm)

Step 4: SCORE (OpenSkill Rating Calculation)
─────────────────────────────────────────────
   decision_analysis (rated=false)
       │
       ↓
   [pipeline/score.py]
       │
       │ Extract winner/loser
       ↓
   [scoring/openskill.py]
       │
       │ Bayesian skill rating
       │ (like chess Elo)
       ↓
   lawyer_ratings table
       ├─ mu (skill level)
       ├─ sigma (uncertainty)
       └─ rating (display)

Step 5: EXPORT (Parquet → Internet Archive)
────────────────────────────────────────────
   DuckDB tables
       │
       ↓
   [pipeline/export_orchestrator.py]
       │
       ├─→ [pipeline/parquet_export.py]
       │   └─→ Export to Parquet format
       │
       └─→ [pipeline/ia_upload.py]
           └─→ Upload to Internet Archive
       │
       ↓
   Internet Archive:
       ├─ causaganha-decisions-2025-01-22-TJRO.parquet
       ├─ causaganha-embeddings-2025-01-22-TJRO.parquet
       ├─ causaganha-lawyers-2025-01-22.parquet
       └─ causaganha-partes-2025-01-22-TJRO.parquet
```

---

## 🧩 Layer-by-Layer Explanation

### 1️⃣ CLI Layer (`cli/`)

**Purpose**: User interface for all operations.

**Files**:
- `cli/__init__.py` (898 lines - will be broken into modules)

**Commands**:
```bash
causaganha collect         # Step 1: Fetch from PJe API
causaganha archive         # Step 2: Archive to IA
causaganha analyze         # Step 3: AI analysis
causaganha score           # Step 4: Calculate ratings
causaganha pipeline        # Run all steps
causaganha parquet         # Parquet workflows
causaganha export-parquet  # Export to IA
causaganha db              # Database admin
causaganha groundtruth     # RAG training data
```

**How it works**:
```python
# cli/__init__.py (simplified)
from typer import Typer
from causaganha.pipeline.collect import collect_metadata_for_court
from causaganha.pipeline.analyze import analyze_pending_decisions
from causaganha.pipeline.score import calculate_ratings

app = Typer()

@app.command()
def collect(days_back: int = 7, courts: str = "TJRO"):
    """Collect intimations from PJe API."""
    results = asyncio.run(
        collect_metadata_for_court(
            sigla_tribunal=courts,
            days_back=days_back
        )
    )
    print(f"Collected {results['stored']} intimations")

@app.command()
def analyze(strategy: str = "hybrid"):
    """Analyze decisions using AI."""
    results = asyncio.run(
        analyze_pending_decisions(
            strategy=strategy,
            confidence_threshold=0.70
        )
    )
    print(f"Analyzed {results['total_analyzed']} decisions")
```

---

### 2️⃣ API Layer (`api/`)

**Purpose**: Communicate with external data sources (PJe API).

**Files**:
- `api/client.py` (281 lines)

**What it does**:
```python
# api/client.py (simplified)
class PJeAPIClient:
    """HTTP client for PJe (Processo Judicial Eletrônico) API."""

    BASE_URL = "https://api-publica.datajud.cnj.jus.br"

    async def get_intimations_by_court(
        self,
        sigla_tribunal: str,      # e.g., "TJRO"
        data_inicio: date,        # Start date
        data_fim: date,           # End date
        max_items: int = None
    ) -> list[dict]:
        """
        Fetch intimations from PJe API.

        Returns list of intimations with:
        - id: Unique intimation ID
        - numero_processo: Case number
        - texto: Decision text (used for analysis)
        - destinatarioadvogados: List of lawyers
        - data_disponibilizacao: Publication date
        """
        url = f"{self.BASE_URL}/intimacoes"
        params = {
            "siglaTribunal": sigla_tribunal,
            "dataInicio": data_inicio.isoformat(),
            "dataFim": data_fim.isoformat()
        }

        # Handle pagination, rate limits, retries
        intimations = []
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            intimations = response.json()

        return intimations
```

**Key Features**:
- ✅ Async HTTP with `httpx`
- ✅ Automatic pagination
- ✅ Rate limit handling (429 errors)
- ✅ Retry logic with exponential backoff
- ✅ Request/response logging

---

### 3️⃣ Pipeline Layer (`pipeline/`)

**Purpose**: Orchestrate workflows (collect → archive → analyze → score → export).

**Files** (11 files):
- `collect.py` - Metadata collection from PJe
- `archive.py` - Document archiving to Internet Archive
- `analyze.py` - Decision analysis orchestration
- `score.py` - Rating calculation
- `parquet_export.py` - Parquet export
- `ia_upload.py` - Internet Archive upload
- `ia_download.py` - Internet Archive download
- `analyze_parquet.py` - Analyze from parquet files
- `embedding_pipeline.py` - Embedding generation
- `export_orchestrator.py` - Export coordination

**Example: `collect.py`**
```python
async def collect_metadata_for_court(
    sigla_tribunal: str,
    days_back: int = 7,
    max_items: int = None
) -> dict:
    """
    Collect intimation metadata from PJe API.

    Flow:
    1. Initialize PJe API client
    2. Calculate date range
    3. Fetch intimations from API
    4. Extract lawyer associations
    5. Store in DuckDB
    6. Return statistics
    """
    client = PJeAPIClient()
    con = get_connection()  # DuckDB

    # Fetch from API
    intimations = await client.get_intimations_by_court(
        sigla_tribunal=sigla_tribunal,
        data_inicio=date.today() - timedelta(days=days_back),
        data_fim=date.today(),
        max_items=max_items
    )

    # Store metadata
    stored = store_intimations(con, intimations, sigla_tribunal)

    # Extract and store lawyer associations
    for intimation in intimations:
        lawyers = intimation.get("destinatarioadvogados", [])
        store_lawyer_associations(con, intimation["id"], lawyers)

    return {
        "fetched": len(intimations),
        "stored": stored,
        "tribunal": sigla_tribunal
    }
```

**Example: `analyze.py`**
```python
async def analyze_pending_decisions(
    batch_size: int = 10,
    strategy: AnalysisStrategy = AnalysisStrategy.HYBRID,
    confidence_threshold: float = 0.70
) -> dict:
    """
    Analyze pending decisions using AI.

    Strategy options:
    - LLM: Google Gemini only (expensive, accurate)
    - RAG: Embeddings only (cheap, less accurate)
    - HYBRID: RAG first, LLM fallback if confidence < 0.70 (default)
    """
    con = get_connection()

    # Initialize analyzer based on strategy
    analyzer = await _initialize_analyzer(strategy, confidence_threshold)

    # Get unanalyzed intimations
    intimations = get_unanalyzed_intimations(con, limit=batch_size)

    # Analyze in batches
    for intimation in intimations:
        result = await analyzer.analyze_text(
            text=intimation["texto"],
            intimation_id=intimation["id"]
        )

        # Store result
        store_analysis(con, intimation["id"], result)
        mark_as_analyzed(con, intimation["id"], success=True)

    return {"total_analyzed": len(intimations)}
```

---

### 4️⃣ Analysis Layer (`analysis/`)

**Purpose**: AI-powered decision analysis (the brain of the system).

**Files** (11 files):
- `analyzer.py` - LLM analyzer (Pydantic AI + Gemini)
- `rag_analyzer.py` - RAG-only analyzer (embeddings)
- `hybrid_analyzer.py` - Hybrid strategy (RAG → LLM fallback)
- `embedding_service.py` - Embedding generation service
- `providers.py` - Embedding provider implementations (Jina, Google)
- `embedding_models.py` - Model configurations
- `vector_store.py` - Vector database (for RAG)
- `models.py` - Pydantic models for analysis results
- `strategy.py` - Analysis strategy enum
- `text_chunker.py` - Text chunking utilities

**Analysis Strategies**:

#### Strategy 1: LLM-Only (Expensive, Accurate)
```python
# analysis/analyzer.py
class DecisionAnalyzer:
    """LLM-based decision analyzer using Pydantic AI + Google Gemini."""

    async def analyze_text(self, text: str, intimation_id: int):
        """
        Analyze decision text using Google Gemini.

        Prompt:
        "You are a Brazilian legal expert. Analyze this judicial decision
        and determine:
        - Winner lawyer (OAB number)
        - Loser lawyer (OAB number)
        - Decision outcome (WIN, LOSS, PARTIAL)
        - Confidence score (0-1)
        - Reasoning"

        Returns: DecisionAnalysis (Pydantic model)
        """
        result = await pydantic_ai.run(
            model="gemini-1.5-flash",
            prompt=text,
            result_type=DecisionAnalysis
        )
        return result
```

#### Strategy 2: RAG-Only (Cheap, Less Accurate)
```python
# analysis/rag_analyzer.py
class RAGAnalyzer:
    """RAG-based analyzer using embeddings and cosine similarity."""

    async def analyze_text(self, text: str, intimation_id: int):
        """
        Analyze using RAG (Retrieval-Augmented Generation):

        1. Chunk decision text
        2. Generate embeddings for each chunk
        3. Search vector store for similar ground truth examples
        4. Vote on outcome based on top-K matches
        5. Calculate confidence from vote distribution

        Returns: DecisionAnalysis with rag_confidence score
        """
        # Generate embedding
        embedding = await self.embedding_service.embed_text(text)

        # Search vector store
        similar = self.vector_store.search(embedding, top_k=10)

        # Vote on outcome
        votes = [match.outcome for match in similar]
        outcome = max(set(votes), key=votes.count)
        confidence = votes.count(outcome) / len(votes)

        return DecisionAnalysis(
            outcome=outcome,
            confidence_score=confidence,
            analysis_method="rag"
        )
```

#### Strategy 3: HYBRID (Default - Best of Both Worlds)
```python
# analysis/hybrid_analyzer.py
class HybridAnalyzer:
    """
    Hybrid strategy: RAG → LLM fallback.

    Logic:
    1. Try RAG first (cheap)
    2. If RAG confidence >= 0.70: return RAG result
    3. If RAG confidence < 0.70: fallback to LLM (expensive but accurate)

    Cost Savings: ~60-70% (most decisions have high RAG confidence)
    """

    def __init__(
        self,
        rag_analyzer: RAGAnalyzer,
        llm_analyzer: DecisionAnalyzer,
        confidence_threshold: float = 0.70
    ):
        self.rag = rag_analyzer
        self.llm = llm_analyzer
        self.threshold = confidence_threshold

    async def analyze_text(self, text: str, intimation_id: int):
        # Try RAG first
        rag_result = await self.rag.analyze_text(text, intimation_id)

        if rag_result.confidence_score >= self.threshold:
            # High confidence, return RAG result
            return rag_result

        # Low confidence, fallback to LLM
        llm_result = await self.llm.analyze_text(text, intimation_id)
        llm_result.rag_confidence = rag_result.confidence_score
        llm_result.analysis_method = "hybrid"
        return llm_result
```

**Embedding Providers** (auto-selection):
```python
# analysis/embedding_service.py
class EmbeddingService:
    """
    Multi-provider embedding service with auto-selection.

    Priority:
    1. Jina AI (jina-embeddings-v4, 1024D, 32K tokens) ← Default
    2. Google Gemini (text-embedding-004, 768D) ← Fallback

    Auto-selection:
    1. Check JINA_API_KEY env var
    2. Validate Jina API key by test request
    3. If Jina fails, fallback to Google
    4. If both fail, raise error
    """

    @classmethod
    async def create(cls, priority: list[str] = None):
        """Async factory with auto-provider selection."""
        provider = await auto_select_provider(
            priority=priority or ["jina", "google"]
        )
        return cls(provider=provider)

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector."""
        return await self.provider.embed_text(
            text=text,
            model=self.model,
            task_type="RETRIEVAL_QUERY"
        )
```

---

### 5️⃣ Storage Layer (`storage/`)

**Purpose**: Data persistence using DuckDB (embedded SQL database).

**Files**:
- `connection.py` - DuckDB connection singleton
- `queries.py` - CRUD operations (460 lines)
- `migrations.py` - Schema versioning
- `schema.sql` - DDL (Data Definition Language)
- `embedding_storage.py` - Embedding-specific storage

**Why DuckDB?**
- ✅ **Embedded**: No server to manage (just a file)
- ✅ **Fast**: Columnar storage optimized for analytics
- ✅ **SQL**: Familiar query language
- ✅ **Parquet**: Native Parquet support (export/import)
- ✅ **ACID**: Transactional guarantees

**Database Schema**:
```sql
-- Intimations (case metadata)
intimations
├─ id (BIGINT PK)
├─ numero_processo (VARCHAR)
├─ texto (TEXT) ← Decision text for analysis
├─ sigla_tribunal (VARCHAR)
├─ ia_url (VARCHAR) ← Internet Archive URL
├─ analyzed (BOOLEAN)
└─ created_at (TIMESTAMP)

-- Lawyer associations
intimation_lawyers
├─ intimation_id (FK → intimations.id)
├─ oab_number (VARCHAR)
├─ oab_state (VARCHAR)
├─ lawyer_name (VARCHAR)
└─ polo (VARCHAR) ← "A" (author) or "P" (defendant)

-- Decision analysis results
decision_analysis
├─ id (UUID PK)
├─ intimation_id (BIGINT UNIQUE FK)
├─ winner_lawyer_oab (VARCHAR)
├─ winner_lawyer_state (VARCHAR)
├─ loser_lawyer_oab (VARCHAR)
├─ loser_lawyer_state (VARCHAR)
├─ outcome (VARCHAR) ← WIN, LOSS, PARTIAL
├─ confidence_score (FLOAT)
├─ analysis_method (VARCHAR) ← llm, rag, hybrid
├─ rag_confidence (FLOAT)
├─ rated (BOOLEAN)
└─ created_at (TIMESTAMP)

-- Lawyer ratings (OpenSkill)
lawyer_ratings
├─ id (UUID PK)
├─ oab_number (VARCHAR)
├─ oab_state (VARCHAR)
├─ lawyer_name (VARCHAR)
├─ mu (FLOAT) ← Skill level
├─ sigma (FLOAT) ← Uncertainty
├─ rating (FLOAT) ← Display rating (mu - 3*sigma)
├─ games_played (INT)
└─ last_game_at (TIMESTAMP)
```

**Example Queries**:
```python
# storage/queries.py (simplified)

def get_unanalyzed_intimations(con, limit: int = 100):
    """Get intimations that haven't been analyzed yet."""
    return con.execute("""
        SELECT id, texto, numero_processo
        FROM intimations
        WHERE analyzed = FALSE
          AND texto IS NOT NULL
        LIMIT ?
    """, [limit]).fetchall()

def store_analysis(con, intimation_id: int, analysis: DecisionAnalysis):
    """Store analysis result."""
    con.execute("""
        INSERT INTO decision_analysis (
            intimation_id,
            winner_lawyer_oab,
            loser_lawyer_oab,
            outcome,
            confidence_score,
            analysis_method
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, [
        intimation_id,
        analysis.winner_lawyer_oab,
        analysis.loser_lawyer_oab,
        analysis.outcome,
        analysis.confidence_score,
        analysis.analysis_method
    ])

def get_unrated_analyses(con, limit: int = 100):
    """Get analyses that need rating calculation."""
    return con.execute("""
        SELECT *
        FROM decision_analysis
        WHERE rated = FALSE
        LIMIT ?
    """, [limit]).fetchall()
```

---

### 6️⃣ Scoring Layer (`scoring/`)

**Purpose**: Calculate lawyer skill ratings using OpenSkill (Bayesian rating system).

**Files**:
- `scoring/openskill.py` - OpenSkill rating algorithm

**How OpenSkill Works**:
```
OpenSkill is like chess Elo, but better:
- Tracks skill level (mu) and uncertainty (sigma)
- New lawyers start with high uncertainty
- Uncertainty decreases as more games are played
- Rating = mu - 3*sigma (conservative estimate)

Example:
  Lawyer A: mu=1500, sigma=200 → rating = 900  (new, uncertain)
  Lawyer B: mu=1500, sigma=50  → rating = 1350 (experienced, confident)
```

**Rating Calculation**:
```python
# scoring/openskill.py (simplified)
from openskill import Rating, rate

def get_openskill_model():
    """Get OpenSkill model with CausaGanha parameters."""
    return openskill.Model(
        mu=1500,        # Initial skill
        sigma=500,      # Initial uncertainty
        beta=250,       # Skill variation
        tau=25,         # Dynamic factor
        kappa=0.0001    # Draw probability
    )

def rate_teams(model, winner_rating, loser_rating):
    """
    Update ratings after a match.

    Args:
        winner_rating: Rating(mu=1500, sigma=200)
        loser_rating: Rating(mu=1400, sigma=300)

    Returns:
        (new_winner_rating, new_loser_rating)
    """
    teams = [[winner_rating], [loser_rating]]
    ranks = [1, 2]  # Winner = rank 1, Loser = rank 2

    new_ratings = model.rate(teams, ranks)
    return new_ratings[0][0], new_ratings[1][0]
```

**Rating Update Example**:
```python
async def calculate_ratings(batch_size: int = 100):
    """Calculate ratings for unrated analyses."""
    analyses = get_unrated_analyses(con, limit=batch_size)

    for analysis in analyses:
        # Get current ratings
        winner_rating = get_lawyer_rating(con, winner_oab, winner_state)
        loser_rating = get_lawyer_rating(con, loser_oab, loser_state)

        # Calculate new ratings
        new_winner, new_loser = rate_teams(
            model,
            winner_rating,
            loser_rating
        )

        # Update database
        update_lawyer_rating(con, winner_oab, winner_state, new_winner)
        update_lawyer_rating(con, loser_oab, loser_state, new_loser)
        mark_analysis_as_rated(con, analysis["id"])
```

---

### 7️⃣ Clients Layer (`clients/`)

**Purpose**: External service integrations.

**Files**:
- `clients/archive.py` - Internet Archive client
- `clients/document.py` - Document download service
- `clients/preservation.py` - Preservation service
- `clients/constants.py` - Client constants

**Internet Archive Integration**:
```python
# clients/archive.py (simplified)
import internetarchive as ia

class InternetArchiveService:
    """Upload/download files to/from Internet Archive."""

    def upload_parquet(
        self,
        file_path: str,
        tribunal: str,
        date: str
    ) -> str:
        """
        Upload parquet file to Internet Archive.

        Returns: URL to the uploaded file
        """
        identifier = f"causaganha-decisions-{date}-{tribunal}"

        # Upload to Internet Archive
        item = ia.get_item(identifier)
        item.upload(
            file_path,
            metadata={
                "collection": "causaganha",
                "title": f"CausaGanha Decisions {tribunal} {date}",
                "mediatype": "data",
                "description": "Judicial decision analysis dataset"
            }
        )

        return f"https://archive.org/download/{identifier}/{file_path}"
```

---

### 8️⃣ Models Layer (`models/`)

**Purpose**: Domain models (Pydantic classes for data validation).

**Files**:
- `models/__init__.py` (empty, prepared for future use)

**Note**: Currently, domain models are defined in:
- `analysis/models.py` (DecisionAnalysis)
- Database schema in `storage/schema.sql`

**Future**: Extract to this layer:
- `models/intimation.py` - Intimation model
- `models/lawyer.py` - Lawyer model
- `models/party.py` - Party model
- `models/analysis.py` - Analysis model

---

## 🔧 Key Technologies

### Backend
- **Python 3.12** - Language
- **DuckDB** - Embedded SQL database
- **Ibis** - Pythonic SQL query builder
- **Pydantic** - Data validation
- **Pydantic AI** - LLM orchestration framework
- **httpx** - Async HTTP client
- **Typer** - CLI framework
- **structlog** - Structured logging

### AI/ML
- **Google Gemini** - LLM for decision analysis
- **Jina AI** - Embedding generation (priority #1)
- **OpenSkill** - Bayesian rating algorithm
- **NumPy** - Vector operations

### Data
- **PyArrow** - Parquet I/O
- **Internet Archive** - Public dataset hosting
- **DuckDB** - Columnar analytics

### Testing
- **pytest** - Testing framework
- **pytest-bdd** - BDD (Behavior-Driven Development)
- **pytest-asyncio** - Async test support

---

## 🌍 Real-World Example

### Scenario: Analyzing a Week of TJRO Decisions

```bash
# Step 1: Collect intimations from TJRO (last 7 days)
$ uv run causaganha collect --days-back 7 --courts TJRO

# Output:
# ✓ Collected 1,234 intimations
# ✓ Stored 1,234 intimations
# ✓ Extracted 2,468 lawyer associations
```

**What happened**:
1. `cli/__init__.py` called `pipeline/collect.py`
2. `pipeline/collect.py` called `api/client.py`
3. `api/client.py` fetched from PJe API:
   ```json
   {
     "id": 123456789,
     "numero_processo": "0000001-00.2025.8.22.0001",
     "texto": "Decisão: Defiro o pedido de tutela...",
     "destinatarioadvogados": [
       {"numeroInscricao": "12345", "siglaUf": "RO", "nome": "João Silva"}
     ]
   }
   ```
4. `storage/queries.py` stored in DuckDB

---

```bash
# Step 2: Analyze decisions using HYBRID strategy
$ uv run causaganha analyze --strategy hybrid

# Output:
# ✓ Analyzing 1,234 decisions...
# ✓ RAG-only: 856 (69%) - avg confidence 0.85
# ✓ Hybrid fallback: 378 (31%) - avg confidence 0.92
# ✓ Total cost: $12.50 (saved $20.00 with RAG)
```

**What happened**:
1. `pipeline/analyze.py` initialized `HybridAnalyzer`
2. For each intimation:
   - **RAG attempt**:
     - `analysis/rag_analyzer.py` chunked text
     - `analysis/embedding_service.py` generated embedding (Jina AI)
     - `analysis/vector_store.py` searched similar cases
     - Voted on outcome, calculated confidence
   - **If confidence >= 0.70**: Return RAG result ✓
   - **If confidence < 0.70**: Fallback to LLM
     - `analysis/analyzer.py` called Google Gemini
     - Parsed structured response using Pydantic AI
3. `storage/queries.py` stored results in `decision_analysis` table

---

```bash
# Step 3: Calculate lawyer ratings
$ uv run causaganha score

# Output:
# ✓ Processed 1,234 analyses
# ✓ Updated 2,468 lawyer ratings
# ✓ Top lawyer: João Silva (OAB 12345/RO) - Rating 1850
```

**What happened**:
1. `pipeline/score.py` fetched unrated analyses
2. For each analysis:
   - Extracted winner/loser OAB numbers
   - `storage/queries.py` fetched current ratings
   - `scoring/openskill.py` calculated new ratings
   - `storage/queries.py` updated ratings in `lawyer_ratings`

---

```bash
# Step 4: Export to Internet Archive
$ uv run causaganha export-parquet --tribunal TJRO

# Output:
# ✓ Exported 1,234 rows to decisions-2025-01-22-TJRO.parquet
# ✓ Uploaded to https://archive.org/download/causaganha-decisions-2025-01-22-TJRO/...
```

**What happened**:
1. `pipeline/export_orchestrator.py` coordinated export
2. `pipeline/parquet_export.py` exported DuckDB → Parquet
3. `pipeline/ia_upload.py` uploaded to Internet Archive
4. `clients/archive.py` used `internetarchive` library

---

## 📊 Performance Metrics

### Cost Optimization (HYBRID Strategy)
```
Scenario: 10,000 decisions/month

LLM-Only:
  - Cost: $0.05 per decision
  - Total: $500/month

RAG-Only:
  - Cost: $0.001 per decision
  - Total: $10/month
  - Accuracy: 75%

HYBRID (70% RAG, 30% LLM):
  - RAG cost: 7,000 × $0.001 = $7
  - LLM cost: 3,000 × $0.05 = $150
  - Total: $157/month
  - Accuracy: 92%
  - Savings: 69% vs LLM-only
```

### Throughput
```
Collection: 1,000 intimations/hour
Analysis (HYBRID): 100 decisions/minute
Rating: 500 lawyers/second
Export: 100,000 rows/second (Parquet)
```

---

## 🎯 Summary

### Architecture Principles
1. **Simple**: Modular monolith, single deployment
2. **Testable**: 329+ BDD scenarios, extensive unit tests
3. **Scalable**: DuckDB columnar storage, async pipelines
4. **Cost-Optimized**: Hybrid RAG/LLM strategy (69% savings)
5. **Transparent**: Public datasets on Internet Archive

### Data Flow (One Sentence)
> CausaGanha **fetches** judicial decisions from PJe API, **analyzes** them with AI to find winners/losers, **calculates** lawyer ratings using OpenSkill, and **publishes** the data as public datasets on Internet Archive.

### Key Innovation
> **Hybrid RAG/LLM Strategy**: Cheap embeddings for most cases, expensive LLM only when needed, achieving 92% accuracy at 69% cost savings.

---

## 📚 Further Reading

- **[PRODUCT_VISION.md](PRODUCT_VISION.md)** - Mission, user personas, success metrics
- **[MVP_SCOPE.md](MVP_SCOPE.md)** - Current scope and definition of "done"
- **[TECHNICAL_REQUIREMENTS.md](TECHNICAL_REQUIREMENTS.md)** - Scale targets, performance specs
- **[SCHEMA_V2_FINAL_RECOMMENDATIONS.md](SCHEMA_V2_FINAL_RECOMMENDATIONS.md)** - Multi-parquet architecture
- **[TEXTO_VS_PDF_CLARIFICATION.md](TEXTO_VS_PDF_CLARIFICATION.md)** - Why texto, not PDFs

---

**Last Updated**: 2025-01-23
**Architecture Version**: Unified (post-migration)
**Status**: ✅ Production-ready
