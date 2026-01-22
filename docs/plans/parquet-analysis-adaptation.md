# Parquet-Based Analysis Adaptation Plan

**Status:** In Development
**Created:** 2026-01-22
**Branch:** `claude/adapt-parquet-analysis-W2VQI`

## Problem Statement

CausaGanha currently analyzes judicial decisions directly from DuckDB after collection from PJe API. However, with parquet files uploaded to Internet Archive, we need to:

1. Support analysis workflows that read from archived parquet files
2. Enable reprocessing of historical data without re-collecting from PJe
3. Provide insights on parquet schema improvements to ease analysis

## Current State

### Data Flow (V2)
```
PJe API → DuckDB (intimations) → Analysis Pipeline → DuckDB (decision_analysis) → Parquet Export → Internet Archive
```

### Parquet Schema (v1)
- **Intimation fields**: id, numero_processo, hash, tribunal, date, texto, PDF link
- **Analysis fields**: winner/loser OAB, decision_type, outcome, confidence_score, analysis_method
- **Partition columns**: partition_date, year, month, day
- **Format**: Snappy compression, 10K row groups, v2.6 Parquet

### Analysis Pipeline
- **Input**: Reads unanalyzed intimations from DuckDB
- **Processing**: Uses LLM/RAG/Hybrid analyzers
- **Output**: Writes to decision_analysis table

## Proposed Solution

### 1. Internet Archive Parquet Downloader

**Module:** `src/causaganha/v2/pipeline/ia_download.py`

**Features:**
- Download parquet files from Internet Archive by date/tribunal
- Local caching to avoid redundant downloads
- Batch download for date ranges
- Retry logic with exponential backoff
- Checksum verification

**API:**
```python
downloader = IAParquetDownloader(cache_dir="./cache")
file_path = await downloader.download(tribunal="TJRO", date="2025-01-15")
files = await downloader.download_range(start_date="2025-01-01", end_date="2025-01-31", tribunal="TJRO")
```

### 2. Parquet-Based Analysis Pipeline

**Module:** `src/causaganha/v2/pipeline/analyze_parquet.py`

**Features:**
- Read parquet files using PyArrow/Ibis
- Filter unanalyzed or low-confidence decisions
- Support all analysis strategies (LLM/RAG/Hybrid)
- Batch processing with configurable size
- Write results to:
  - New parquet files (for distributed workflows)
  - DuckDB (for integration with existing pipeline)
  - Both (for hybrid scenarios)

**API:**
```python
# Analyze from parquet file
results = await analyze_from_parquet(
    parquet_path="./cache/causaganha-2025-01-15-TJRO.parquet",
    strategy=AnalysisStrategy.HYBRID,
    output_mode="parquet",  # or "duckdb" or "both"
    filter_unanalyzed=True,  # Only analyze rows without analysis
    confidence_threshold=0.70
)

# Analyze from Internet Archive
results = await analyze_from_ia(
    tribunal="TJRO",
    date="2025-01-15",
    strategy=AnalysisStrategy.HYBRID,
    auto_download=True
)
```

### 3. Parquet Format Improvements

#### Current Limitations for Analysis

1. **Missing PDF content**: Only stores PDF link, not content
   - **Impact**: Analysis from parquet requires external PDF download
   - **Frequency**: Every LLM analysis needs PDF access

2. **Flat text field**: Decision text stored as single string
   - **Impact**: No structure for sections (facts, reasoning, decision)
   - **Frequency**: Affects RAG quality and embedding generation

3. **No embeddings**: Pre-computed embeddings not stored
   - **Impact**: RAG analysis requires re-embedding every time
   - **Frequency**: Every RAG analysis (most common mode)

4. **Limited lawyer context**: Only OAB numbers, no names or historical stats
   - **Impact**: Can't do lawyer-aware analysis without joining rating table
   - **Frequency**: Every analysis that needs lawyer context

5. **No decision confidence breakdown**: Single confidence_score
   - **Impact**: Can't understand which parts of analysis are uncertain
   - **Frequency**: All quality assessment workflows

#### Recommended Improvements (Priority Order)

##### P0: Add Decision Text Embeddings
**Change:** Add `texto_embedding` column (array[float])
**Schema:**
```python
("texto_embedding", pa.list_(pa.float32(), 1024))  # Jina v3 default
```
**Benefits:**
- Instant RAG analysis without re-embedding (saves ~$0.000008 per decision)
- Enables similarity search directly on parquet
- Reduces cold-start latency for analysis

**ETL Impact:** Minimal
- Compute embeddings during export (already in pipeline)
- Increases file size by ~4KB per row (1024 floats × 4 bytes)
- For 10K rows: +40MB per file

##### P1: Add Structured Decision Sections
**Change:** Add `texto_sections` struct column
**Schema:**
```python
texto_sections = pa.struct([
    ("full_text", pa.string()),
    ("facts", pa.string()),
    ("reasoning", pa.string()),
    ("decision", pa.string()),
    ("extracted_via", pa.string())  # "llm" or "heuristic"
])
```
**Benefits:**
- Better context for RAG (embed only relevant sections)
- Improved LLM analysis (focus on decision section)
- Enable section-specific confidence scores

**ETL Impact:** Medium
- Requires LLM call during export for extraction
- Adds ~$0.0001 per decision (using Gemini Flash)
- Can fallback to heuristic extraction if budget constrained

##### P2: Add Lawyer Enrichment
**Change:** Add `winner_lawyer` and `loser_lawyer` struct columns
**Schema:**
```python
lawyer_info = pa.struct([
    ("oab", pa.string()),
    ("state", pa.string()),
    ("name", pa.string()),
    ("current_rating", pa.float32()),
    ("total_cases", pa.int32()),
    ("win_rate", pa.float32())
])
```
**Benefits:**
- Self-contained analysis without joining rating table
- Historical tracking (snapshot rating at decision time)
- Better analysis context for LLM

**ETL Impact:** Minimal
- Join with lawyer_ratings table during export
- No additional API calls
- Increases file size by ~100 bytes per row

##### P3: Add Confidence Breakdown
**Change:** Expand confidence tracking
**Schema:**
```python
confidence_breakdown = pa.struct([
    ("overall", pa.float32()),
    ("winner_identification", pa.float32()),
    ("loser_identification", pa.float32()),
    ("outcome_classification", pa.float32()),
    ("decision_type", pa.float32())
])
```
**Benefits:**
- Identify specific weak points in analysis
- Better filtering for reanalysis
- Quality metrics for A/B testing

**ETL Impact:** Minimal
- Already computed by analyzers (just store more detail)
- Adds ~20 bytes per row

##### P4: Add PDF Content (Optional/Large Files)
**Change:** Store base64-encoded PDF content
**Schema:**
```python
("pdf_content_base64", pa.binary())
("pdf_size_bytes", pa.int32())
```
**Benefits:**
- Fully self-contained parquet files
- No external dependencies for analysis
- Enable offline/air-gapped analysis

**ETL Impact:** Large
- Dramatically increases file size (PDFs average ~500KB)
- For 10K rows: +5GB per file (10x increase)
- Storage costs increase significantly
**Recommendation:** Only for special "complete" exports, not daily exports

### 4. Implementation Phases

#### Phase 1: Basic Parquet Analysis (Current Sprint)
- [ ] Implement IAParquetDownloader
- [ ] Implement analyze_from_parquet() with existing schema
- [ ] Add CLI commands for parquet analysis
- [ ] Write tests for download and analysis workflows

#### Phase 2: Schema v2 with Embeddings (Next Sprint)
- [ ] Update ParquetExporter to include embeddings
- [ ] Implement fast RAG analysis from parquet (no re-embedding)
- [ ] Migration strategy for existing parquet files
- [ ] Benchmark performance improvements

#### Phase 3: Full Schema Enhancements (Future)
- [ ] Implement structured text sections
- [ ] Add lawyer enrichment
- [ ] Add confidence breakdown
- [ ] Schema versioning and migration tools

## Architecture Decisions

### 1. Dual-Mode Analysis Support
Keep both DuckDB and parquet analysis pipelines:
- **DuckDB mode**: Real-time analysis for daily collection
- **Parquet mode**: Batch reprocessing for historical data

### 2. Output Flexibility
Support multiple output targets:
- Parquet files: For distributed/stateless workflows
- DuckDB: For integration with existing rating system
- Both: For hybrid scenarios

### 3. Backward Compatibility
Maintain schema versioning:
- Schema v1: Current format (no breaking changes)
- Schema v2: Add embeddings + lawyer enrichment
- Schema v3: Add structured sections + confidence breakdown

Use schema version metadata in parquet files for compatibility.

### 4. Caching Strategy
Implement smart caching:
- Cache downloaded parquet files by hash
- Cache analysis results to avoid reprocessing
- Configurable cache TTL and size limits

## Success Metrics

### Functional Requirements
- ✅ Can analyze decisions from Internet Archive parquet
- ✅ No dependency on live PJe API for reanalysis
- ✅ Support all existing analysis strategies
- ✅ Results compatible with existing rating pipeline

### Performance Requirements
- Download parquet file: < 30s for 10K decisions
- Analysis throughput: Same as DuckDB mode (>100 decisions/min)
- Memory usage: < 2GB for processing 10K decisions
- Cache hit rate: > 80% for repeated analysis

### Quality Requirements
- Analysis accuracy: Same as DuckDB mode
- No data loss during parquet roundtrip
- Schema validation on read/write
- Comprehensive error handling and logging

## Testing Strategy

### Unit Tests
- IAParquetDownloader download logic
- Parquet read/write with schema validation
- Analysis pipeline with mocked data
- Output format conversion

### Integration Tests
- End-to-end workflow: IA download → analyze → write results
- DuckDB integration (write results to DB)
- Cache behavior (hits, misses, eviction)
- Error recovery (failed downloads, corrupt files)

### Performance Tests
- Benchmark download speeds
- Compare analysis throughput vs DuckDB mode
- Memory profiling for large files
- Cache effectiveness measurement

## Migration Strategy

### For Existing Deployments
1. **Phase 1**: Deploy parquet analysis as opt-in feature
2. **Phase 2**: Run parallel analysis (DuckDB + parquet) for validation
3. **Phase 3**: Switch default for reanalysis to parquet mode
4. **Phase 4**: Deprecate redundant DuckDB analysis for archived data

### For Existing Parquet Files
1. **Schema v1**: Continue supporting current format
2. **Schema v2**: Re-export with embeddings (optional, on-demand)
3. Provide migration tool: `causaganha parquet migrate --schema v2 --date-range 2025-01-01:2025-12-31`

## Open Questions

1. **Should we support streaming analysis** (process parquet in chunks)?
   - Pro: Lower memory usage for large files
   - Con: More complex implementation
   - **Decision**: Start with full-file mode, add streaming if needed

2. **Where to store parquet analysis results?**
   - Option A: New parquet file (self-contained)
   - Option B: DuckDB only (existing workflow)
   - Option C: Both (configurable)
   - **Decision**: Implement Option C (configurable output)

3. **How to handle schema evolution?**
   - Option A: Strict versioning (break on mismatch)
   - Option B: Lenient reading (ignore unknown columns)
   - Option C: Auto-migration (update schema on read)
   - **Decision**: Option B initially, Option C later

4. **Should we cache embeddings separately?**
   - Pro: Avoid re-embedding, faster RAG
   - Con: Cache invalidation complexity
   - **Decision**: Include embeddings in schema v2 parquet

## Resources

### Documentation
- [PyArrow Parquet Docs](https://arrow.apache.org/docs/python/parquet.html)
- [Internet Archive Python Library](https://archive.org/services/docs/api/internetarchive/)
- [DuckDB Parquet Support](https://duckdb.org/docs/data/parquet)

### Related Files
- `v2/pipeline/parquet_export.py`: Current parquet export logic
- `v2/pipeline/ia_upload.py`: Internet Archive upload
- `v2/pipeline/analyze.py`: Current DuckDB analysis pipeline
- `v2/storage/schema.sql`: Database schema

### Examples
- Schema v1: `causaganha-2025-01-15-TJRO.parquet`
- IA Item URL: `https://archive.org/details/causaganha-2025-01-15-TJRO`

## Timeline

- **Week 1**: Implement Phase 1 (basic parquet analysis)
- **Week 2**: Write tests and documentation
- **Week 3**: Schema v2 design and implementation
- **Week 4**: Performance testing and optimization

## Approval

- [ ] Technical Lead Review
- [ ] Product Owner Sign-off
- [ ] Security Review (API keys, data access)
- [ ] Ready for Implementation
