# Local Pipeline Testing & Performance Optimization Guide

This guide explains how to run and measure the CausaGanha pipeline locally to identify optimization opportunities.

## Quick Start

### Prerequisites

You need IA (Internet Archive) credentials:

```bash
export IAS3_ACCESS_KEY="your-ia-key"
export IAS3_SECRET_KEY="your-ia-secret"

# Optional: for embeddings
export JINA_API_KEY="your-jina-key"
export GOOGLE_API_KEY="your-google-key"
```

### Run Individual Steps

```bash
# Test individual components
make -f Makefile.local collect        # Download 5 items from DJEN
make -f Makefile.local consolidate    # Convert 3 ZIPs to Parquet
make -f Makefile.local embed          # Generate embeddings for 50 decisions
make -f Makefile.local catalog        # Build catalog/manifest
make -f Makefile.local dashboard      # Generate dashboard cache
```

### Run Full Pipeline

```bash
# Small dataset (quick testing)
make -f Makefile.local full

# Larger dataset (realistic performance)
make -f Makefile.local full-large

# With detailed performance analysis
make -f Makefile.local analyze
```

## Performance Analysis

The analyzer measures:

| Metric | Importance | How to Improve |
|--------|-----------|-----------------|
| **Duration** | Critical | Identify slow steps, parallelize, batch operations |
| **Memory Peak** | Important | Stream processing, reduce intermediate copies |
| **Output Size** | Moderate | Improve compression, deduplicate data |
| **Network Calls** | Critical | Batch API requests, cache results, use bulk endpoints |
| **File I/O** | Important | Stream to disk, avoid temporary copies |

### Interpreting Results

```
Performance results are saved to: pipeline_performance.json

{
  "total_duration_sec": 145.32,
  "steps": [
    {
      "name": "COLLECT",
      "duration_sec": 45.21,
      "memory_peak_mb": 250.5,
      "files_created": 5,
      "bytes_created": 1024000,
      "success": true
    },
    ...
  ]
}
```

**Red flags:**
- Any step > 50 seconds = needs optimization
- Memory > 1000 MB = streaming/batching issues
- Too many network calls = batch requests

## Step-by-Step Optimization Process

### Phase 1: Measure Baseline (Current Performance)

```bash
make -f Makefile.local analyze > baseline.txt
```

Record the metrics:
- Total time
- Slowest 3 steps
- Peak memory usage

### Phase 2: Identify Bottlenecks

Look for steps where:
1. **Time > 50 seconds** → CPU/I/O bound
2. **Memory > 500 MB** → Inefficient data structures
3. **Files > 20** → Too many intermediate files

### Phase 3: Implement Optimization

For each bottleneck:

#### COLLECT Step (Typical: 20-45 seconds)

**Bottleneck**: Network latency from DJEN server

```python
# Current: Download 1 file at a time
def collect_current():
    for date in dates:
        for tribunal in tribunals:
            download_file(date, tribunal)  # ~1 request per file
            # Total: 365 dates × 91 tribunals = 33,215 requests/year

# Optimized: Batch requests with async
async def collect_optimized():
    tasks = []
    for date in dates:
        for tribunal in tribunals:
            tasks.append(download_file_async(date, tribunal))
    await asyncio.gather(*tasks, return_exceptions=True)
    # Same requests, but parallel → 10-20x speedup
```

**Expected improvement**: 45s → 5-10s for small batches

#### CONSOLIDATE Step (Typical: 30-60 seconds)

**Bottleneck**: Sequential Parquet export

```python
# Current: Export tables one at a time
for table_name in TABLES:
    con.execute(f"COPY {table_name} TO '{path}' FORMAT PARQUET")
    # If 10 tables × 5s each = 50s total

# Optimized: Parallel export (ThreadPoolExecutor)
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(export_table, con, table_name)
        for table_name in TABLES
    ]
    for f in futures:
        f.result()
    # Same work, parallel → 4-5x speedup (5s max)
```

**Expected improvement**: 50s → 10-15s

#### CATALOG Step (Typical: 60+ seconds - SLOWEST)

**Bottleneck**: Full rebuild of 52K+ records every run

```python
# Current: Rebuild entire manifest every cycle
SELECT COUNT(*) FROM djen_files  # 52K+ rows
CREATE TABLE manifest AS SELECT * FROM djen_files  # Full scan
COPY manifest TO 'manifest.parquet'  # Full export

# Optimized: Incremental updates
SELECT * FROM djen_files
WHERE created_at > last_update_time  # Only new/changed
MERGE INTO manifest USING delta  # Incremental update
COPY manifest TO 'manifest.parquet' (COMPRESSION ZSTD)
# Only new records → 80-90% faster
```

**Expected improvement**: 60s → 10-15s

#### DASHBOARD Step (Typical: 10-20 seconds)

**Bottleneck**: Making 3 separate HTTP requests

```python
# Current: 3 sequential API calls
data = fetch_json(IA_SEARCH_URL)     # 5s
data = fetch_json(GITHUB_API)        # 3s
manifest = load_parquet(URL)         # 8s
# Total: 16s serial

# Optimized: Parallel requests
import httpx
async with httpx.AsyncClient() as client:
    ia, github, manifest = await asyncio.gather(
        client.get(IA_SEARCH_URL),
        client.get(GITHUB_API),
        load_parquet_async(URL),
    )
# Same work, parallel → 2-3x speedup
```

**Expected improvement**: 16s → 8s

### Phase 4: Test Improvements

After each optimization:

```bash
# Run small test
make -f Makefile.local <step>

# Run full analysis
make -f Makefile.local analyze

# Compare with baseline
diff -u baseline.txt current.txt
```

## Measurement Checklists

### For Quick Changes (< 5 minutes)

- [ ] Time before: `time <command>`
- [ ] Make change
- [ ] Time after: `time <command>`
- [ ] Calculate speedup: `before / after`

### For Major Changes (> 5 minutes)

- [ ] Run full baseline: `make -f Makefile.local analyze`
- [ ] Implement changes
- [ ] Run full test: `make -f Makefile.local analyze`
- [ ] Save results: `cp pipeline_performance.json performance_v2.json`
- [ ] Compare: `jq '.total_duration_sec' performance_v*.json`

### Key Metrics to Track

```bash
# Extract key metrics from results
jq '.steps[] | select(.name=="CONSOLIDATE") | .duration_sec' pipeline_performance.json
jq '.total_duration_sec' pipeline_performance.json
jq '.steps[].memory_peak_mb | max' pipeline_performance.json
```

## Optimization Priority Matrix

| Step | Current | Potential | Priority | Effort |
|------|---------|-----------|----------|--------|
| COLLECT | 45s | 5-10s | HIGH | LOW |
| CONSOLIDATE | 50s | 10-15s | HIGH | MEDIUM |
| EMBED | varies | varies | MEDIUM | MEDIUM |
| CATALOG | 60s | 10-15s | CRITICAL | MEDIUM |
| DASHBOARD | 16s | 8s | LOW | LOW |

**Recommended order**:
1. CATALOG (biggest impact, moderate effort)
2. CONSOLIDATE (parallel export, easy)
3. COLLECT (async batch, medium effort)
4. DASHBOARD (easy parallel, low impact)

## Success Metrics

Once optimized:

| Target | Current | Goal | Gain |
|--------|---------|------|------|
| Total pipeline | ~200s | <60s | 3.3x |
| Per-cycle collection | 45s | 5s | 9x |
| Catalog update | 60s | 12s | 5x |
| Memory peak | 500 MB | 200 MB | 2.5x |
| API calls (per cycle) | ~100+ | <10 | 10x |

## Troubleshooting

### "No work to do" errors

These are OK - means the dataset is small/complete. Test with:

```bash
# Force consolidation of a past date
cd pipeline-output
uv run python ../scripts/pipeline/consolidate.py --date 2026-01-20 --force
```

### "Network error" or "Timeout"

Likely DJEN proxy or IA slowness. Check:

```bash
# Test connectivity
curl -I https://archive.org/services/search/v1/scrape
curl -I https://djen-proxy-mhgmawcn3a-rj.a.run.app/health
```

### Out of memory

Reduce batch sizes:

```bash
make -f Makefile.local collect  # Uses --max-items 5 (smallest)
# Or edit Makefile.local to use smaller --max-* values
```

## Next Steps

1. **Establish baseline**: Run `make analyze` and save results
2. **Identify worst bottleneck**: Look at `duration_sec` in output
3. **Implement ONE optimization**: Start with easiest wins
4. **Measure improvement**: Compare new results vs baseline
5. **Iterate**: Repeat until target metrics reached

## Advanced Topics

### Profiling CPU

```bash
python -m cProfile -s cumtime scripts/pipeline/consolidate.py --backfill --force --max-zips 2
```

### Profiling Memory

```bash
pip install memory-profiler
python -m memory_profiler scripts/pipeline/consolidate.py --backfill --force --max-zips 2
```

### Distributed Testing

For multi-machine testing:

```bash
# Machine 1: Run full pipeline
make -f Makefile.local full-large

# Machine 2: Run with different resources
# Measure network impact, shared resource contention, etc.
```

---

**Questions?** Check the pipeline logs in `pipeline-output/` or run individual steps with `-v` flag for verbose output.
