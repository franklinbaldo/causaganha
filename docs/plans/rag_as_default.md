# RAG as Default Analysis Method - Implementation Plan

## Context

CausaGanha V2 currently uses LLM-based analysis (Pydantic AI + Gemini) as the only method for decision classification. Recent work has validated a RAG-based approach achieving **83.3% accuracy with 98.1% cost reduction** ($0.000008 vs $0.000420 per decision).

The RAG implementation exists as standalone scripts (`scripts/batch_embed_decisions.py`, `scripts/classify_from_batch_embeddings.py`) but is not integrated into the V2 pipeline or CLI.

## Problem

- **High operational costs**: LLM analysis at scale costs ~$420 per 1M decisions
- **RAG not accessible**: Users cannot leverage the cost-efficient RAG method via CLI
- **No hybrid strategy**: Cannot combine RAG (fast/cheap) with LLM (accurate) for optimal cost/accuracy
- **Scattered implementation**: RAG logic lives in scripts, not in core modules

## Objectives

1. **Make RAG the default analysis method** for decision classification
2. **Implement hybrid strategy**: RAG first with LLM fallback for low-confidence cases
3. **Integrate into V2 architecture**: Move RAG logic into `src/causaganha/v2/analysis/`
4. **Preserve LLM option**: Keep LLM as alternative strategy via CLI flags
5. **Ensure testability**: Comprehensive test coverage for RAG components
6. **Maintain observability**: Track method usage, costs, and confidence metrics

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Default cost per decision | ≤$0.000010 | Cost tracking in DB |
| RAG usage rate | ≥70% | Count by method in analysis table |
| Accuracy vs ground truth | ≥83% | Validation script |
| High-confidence classifications | ≥60% | `confidence_score >= 0.70` |
| LLM fallback rate | ≤30% | Low-confidence count |

## Detailed Plan

### Phase 1: Core RAG Module Implementation

#### 1.1 Create RAG Analyzer Module

**File**: `src/causaganha/v2/analysis/rag_analyzer.py`

**Components**:
- `RAGAnalyzer` class with methods:
  - `__init__(db_path, ground_truth_table, k_neighbors, confidence_threshold)`
  - `async analyze_text(text: str, intimation_id: int) -> DecisionAnalysis`
  - `async analyze_batch(texts: list[str], ids: list[int]) -> list[DecisionAnalysis]`
  - `_chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]`
  - `_embed_chunks(chunks: list[str]) -> list[list[float]]`
  - `_classify_with_knn(embeddings: list[list[float]]) -> dict`

**Key Design Decisions**:
- Use Google Embeddings API (text-embedding-004) for online embeddings
- LanceDB for vector store (already proven in scripts)
- Async/await pattern to match existing V2 architecture
- Return same `DecisionAnalysis` model as LLM analyzer for compatibility

#### 1.2 Create Embedding Service

**File**: `src/causaganha/v2/analysis/embedding_service.py`

**Purpose**: Centralize embedding generation logic

**Components**:
- `EmbeddingService` class:
  - `async embed_text(text: str, task_type: str) -> list[float]`
  - `async embed_batch(texts: list[str]) -> list[list[float]]`
  - `_add_contextual_prefix(text: str) -> str`
  - Rate limiting and retry logic

**Configuration**:
```python
EMBEDDING_CONFIG = {
    "model": "text-embedding-004",
    "chunk_size": 500,
    "chunk_overlap": 100,
    "task_type_query": "RETRIEVAL_QUERY",
    "task_type_document": "RETRIEVAL_DOCUMENT",
    "contextual_prefix": "Analise esta parte da decisão judicial para classificar o resultado...",
}
```

#### 1.3 Create Vector Store Manager

**File**: `src/causaganha/v2/analysis/vector_store.py`

**Purpose**: Abstract LanceDB operations

**Components**:
- `VectorStore` class:
  - `connect(db_path: str) -> None`
  - `create_table(name: str, schema: Schema) -> None`
  - `add_documents(table_name: str, documents: list[dict]) -> None`
  - `search(table_name: str, query_vector: list[float], k: int) -> list[dict]`
  - `table_exists(name: str) -> bool`

#### 1.4 Update Analysis Models

**File**: `src/causaganha/v2/analysis/models.py`

**Add fields to track analysis method**:
```python
class DecisionAnalysis(BaseModel):
    # ... existing fields ...

    # New fields for RAG tracking
    analysis_method: str = "llm"  # "llm", "rag", or "hybrid"
    rag_confidence: float | None = None
    rag_votes: dict[str, int] | None = None
```

### Phase 2: Hybrid Strategy Implementation

#### 2.1 Create Strategy Enum

**File**: `src/causaganha/v2/analysis/strategy.py`

```python
from enum import Enum

class AnalysisStrategy(str, Enum):
    """Analysis method selection strategy."""
    LLM = "llm"          # Use LLM only (expensive, accurate)
    RAG = "rag"          # Use RAG only (cheap, good)
    HYBRID = "hybrid"    # RAG first, LLM fallback (optimal)
    AUTO = "auto"        # Same as HYBRID (default)
```

#### 2.2 Create Hybrid Analyzer

**File**: `src/causaganha/v2/analysis/hybrid_analyzer.py`

```python
class HybridAnalyzer:
    """Combines RAG and LLM for optimal cost/accuracy."""

    def __init__(
        self,
        rag_analyzer: RAGAnalyzer,
        llm_analyzer: DecisionAnalyzer,
        confidence_threshold: float = 0.70,
    ):
        self.rag = rag_analyzer
        self.llm = llm_analyzer
        self.threshold = confidence_threshold

    async def analyze_text(
        self,
        text: str,
        intimation_id: int,
        pdf_url: str | None = None,
    ) -> DecisionAnalysis:
        """Analyze using hybrid strategy."""

        # Step 1: Try RAG (cheap)
        rag_result = await self.rag.analyze_text(text, intimation_id)

        # Step 2: If confidence high, use RAG
        if rag_result.rag_confidence >= self.threshold:
            rag_result.analysis_method = "rag"
            return rag_result

        # Step 3: If confidence low, fallback to LLM
        if pdf_url:
            llm_result = await self.llm.analyze_pdf(pdf_url, intimation_id)
            llm_result.analysis_method = "hybrid"
            llm_result.rag_confidence = rag_result.rag_confidence
            return llm_result
        else:
            # No PDF available, return RAG result with warning
            rag_result.analysis_method = "rag_low_confidence"
            return rag_result
```

### Phase 3: CLI and Pipeline Integration

#### 3.1 Update Analyze Pipeline

**File**: `src/causaganha/v2/pipeline/analyze.py`

**Changes**:
1. Add `strategy` parameter to `analyze_pending_decisions()`
2. Instantiate appropriate analyzer based on strategy
3. Track method usage statistics

```python
async def analyze_pending_decisions(
    con: ibis.BaseBackend,
    limit: int = 10,
    strategy: AnalysisStrategy = AnalysisStrategy.HYBRID,
    confidence_threshold: float = 0.70,
) -> dict:
    """Analyze decisions using specified strategy."""

    # Initialize analyzers based on strategy
    if strategy == AnalysisStrategy.LLM:
        analyzer = DecisionAnalyzer()
    elif strategy == AnalysisStrategy.RAG:
        analyzer = RAGAnalyzer(db_path="data/lancedb")
    else:  # HYBRID or AUTO
        rag = RAGAnalyzer(db_path="data/lancedb")
        llm = DecisionAnalyzer()
        analyzer = HybridAnalyzer(rag, llm, confidence_threshold)

    # ... rest of implementation

    # Track statistics
    stats = {
        "total": len(results),
        "rag_used": sum(1 for r in results if r.analysis_method == "rag"),
        "llm_used": sum(1 for r in results if r.analysis_method in ["llm", "hybrid"]),
        "cost_rag": rag_count * 0.000008,
        "cost_llm": llm_count * 0.000420,
    }

    return stats
```

#### 3.2 Update CLI Commands

**File**: `src/causaganha/cli.py`

**Add flags to `analyze` command**:
```python
@cli.command()
@click.option(
    "--strategy",
    type=click.Choice(["llm", "rag", "hybrid", "auto"]),
    default="hybrid",
    help="Analysis strategy: llm (expensive), rag (cheap), hybrid (optimal)",
)
@click.option(
    "--confidence-threshold",
    type=float,
    default=0.70,
    help="Confidence threshold for hybrid strategy (0.0-1.0)",
)
@click.option("--limit", type=int, default=10)
def analyze(strategy: str, confidence_threshold: float, limit: int):
    """Analyze pending decisions using AI."""

    strategy_enum = AnalysisStrategy(strategy)

    # ... implementation
```

#### 3.3 Add Ground Truth Management Commands

**New CLI commands**:
```bash
# Initialize ground truth from high-confidence LLM results
causaganha groundtruth init --min-confidence 0.90 --limit 100

# Index ground truth for RAG
causaganha groundtruth index

# Validate RAG accuracy
causaganha groundtruth validate

# Expand ground truth
causaganha groundtruth expand --target 500
```

### Phase 4: Database Schema Updates

#### 4.1 Update decision_analysis Table

**Migration**: Add columns to track analysis method

```sql
ALTER TABLE decision_analysis
ADD COLUMN analysis_method VARCHAR DEFAULT 'llm';

ALTER TABLE decision_analysis
ADD COLUMN rag_confidence DOUBLE;

ALTER TABLE decision_analysis
ADD COLUMN rag_votes_json VARCHAR;
```

#### 4.2 Create Vector Store Metadata Table

**Purpose**: Track ground truth and vector store state

```sql
CREATE TABLE IF NOT EXISTS vector_store_metadata (
    id INTEGER PRIMARY KEY,
    table_name VARCHAR NOT NULL,
    total_documents INTEGER NOT NULL,
    total_chunks INTEGER NOT NULL,
    last_indexed TIMESTAMP NOT NULL,
    embedding_model VARCHAR NOT NULL,
    outcome_distribution_json VARCHAR  -- {"WIN": 150, "LOSS": 30, ...}
);
```

### Phase 5: Testing

#### 5.1 Unit Tests

**File**: `tests/v2/analysis/test_rag_analyzer.py`
- Test chunking logic
- Test embedding generation (mocked)
- Test k-NN classification
- Test confidence calculation

**File**: `tests/v2/analysis/test_hybrid_analyzer.py`
- Test strategy selection logic
- Test RAG → LLM fallback
- Test cost tracking

**File**: `tests/v2/analysis/test_vector_store.py`
- Test LanceDB connection
- Test table creation
- Test search operations

#### 5.2 Integration Tests

**File**: `tests/integration/test_rag_pipeline.py`
- Test full RAG pipeline with sample ground truth
- Test hybrid pipeline with mock LLM
- Verify database updates

#### 5.3 E2E Tests

**File**: `tests/e2e/test_rag_lifecycle.py`
- Test complete lifecycle: collect → archive → analyze (RAG) → score
- Verify cost savings
- Validate accuracy against ground truth

### Phase 6: Documentation and Migration

#### 6.1 Update Documentation

**Files to update**:
- `README.md`: Update usage examples to show RAG as default
- `docs/architecture.md`: Add RAG components diagram
- `docs/cost_optimization.md`: Document cost savings
- `CLAUDE.md`: Update development guidelines

#### 6.2 Migration Guide

**File**: `docs/guides/rag_migration.md`

Content:
1. How to initialize ground truth
2. How to switch between strategies
3. Expected behavior changes
4. Performance comparison
5. Troubleshooting

#### 6.3 User Guide

**File**: `docs/guides/analysis_strategies.md`

Content:
- When to use each strategy
- Cost/accuracy trade-offs
- How to tune confidence threshold
- How to expand ground truth

## Implementation Order

### Week 1: Foundation
1. Create `rag_analyzer.py` (move logic from scripts)
2. Create `embedding_service.py`
3. Create `vector_store.py`
4. Add unit tests

### Week 2: Hybrid Strategy
1. Create `strategy.py` and `hybrid_analyzer.py`
2. Update `models.py` with new fields
3. Add integration tests
4. Update database schema

### Week 3: Integration
1. Update `analyze.py` pipeline
2. Update `cli.py` with new commands
3. Add ground truth management commands
4. Add E2E tests

### Week 4: Polish & Documentation
1. Update all documentation
2. Create migration guide
3. Add monitoring/observability
4. Performance testing and optimization

## Risks & Mitigation

### Risk 1: Ground Truth Quality
**Impact**: Low-quality ground truth → poor RAG accuracy

**Mitigation**:
- Start with high-confidence LLM results (≥0.90)
- Manual validation of initial 30-50 decisions
- Continuous accuracy monitoring
- Gradual expansion strategy

### Risk 2: Vector Store Performance
**Impact**: Slow k-NN search at scale

**Mitigation**:
- LanceDB is optimized for vector search
- Monitor query latency
- Add caching layer if needed
- Consider index tuning (IVF, HNSW)

### Risk 3: Embedding API Rate Limits
**Impact**: Analysis pipeline throttled

**Mitigation**:
- Use batch embedding for large volumes
- Implement exponential backoff
- Support multiple API keys
- Cache embeddings in DB

### Risk 4: Strategy Confusion
**Impact**: Users don't understand when to use each strategy

**Mitigation**:
- Good defaults (hybrid)
- Clear CLI help text
- Comprehensive documentation
- Examples for each use case

### Risk 5: Cost Calculation Accuracy
**Impact**: Incorrect cost savings reporting

**Mitigation**:
- Track actual API usage
- Log all API calls with costs
- Regular cost audits
- Comparison reports

## Rollback Plan

If RAG causes issues:

1. **Immediate**: CLI flag `--strategy llm` reverts to LLM-only
2. **Configuration**: Environment variable `CAUSAGANHA_DEFAULT_STRATEGY=llm`
3. **Code**: Revert to previous DecisionAnalyzer in pipeline
4. **Data**: RAG results stored separately, can be re-analyzed with LLM

## Success Criteria

✅ RAG achieves ≥83% accuracy on validation set
✅ Hybrid strategy used in ≥70% of analyses
✅ Cost per decision reduced to ≤$0.000010
✅ All tests passing (unit, integration, E2E)
✅ Documentation complete and reviewed
✅ Zero breaking changes to existing V2 API
✅ CLI backwards compatible (LLM still available)

## Open Questions

1. **Batch Embeddings**: Should we also support batch embedding pipeline for historical analysis?
   - *Decision*: Yes, keep as separate command for bulk processing

2. **Ground Truth Size**: What's the optimal initial size?
   - *Recommendation*: Start with 50-100, expand to 200-500 based on accuracy

3. **Confidence Threshold**: Should this be configurable per-court?
   - *Decision*: Start global, add per-court config later if needed

4. **LLM Fallback**: Should we cache failed RAG results to avoid re-processing?
   - *Decision*: Yes, track in DB to avoid duplicate LLM calls

## Next Steps After Completion

1. **Expand Ground Truth**: Target 500+ validated decisions
2. **Fine-tune Embeddings**: Court-specific fine-tuning for accuracy boost
3. **Multi-lingual Support**: Adapt for other Brazilian tribunals
4. **Batch Processing**: Optimize for historical data analysis (millions of decisions)
5. **Active Learning**: Automatically add high-confidence results to ground truth
