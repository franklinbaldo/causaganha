# Quick Start: Local Pipeline Testing

## One-Liner Setup

```bash
cd causaganha
bash test_pipeline.sh full
```

This will:
1. ✓ Load your IA credentials from ../.env
2. ✓ Download 5 items from DJEN
3. ✓ Convert to Parquet (small batch)
4. ✓ Generate embeddings (50 decisions)
5. ✓ Build catalog manifest
6. ✓ Generate dashboard cache

**Expected duration**: ~5-10 minutes

## Test Individual Steps

```bash
# Download from DJEN proxy
bash test_pipeline.sh collect

# Convert ZIPs to Parquet
bash test_pipeline.sh consolidate

# Generate embeddings
bash test_pipeline.sh embed

# Build manifest/catalog
bash test_pipeline.sh catalog

# Generate dashboard cache
bash test_pipeline.sh dashboard
```

## Performance Analysis

```bash
bash test_pipeline.sh analyze
```

Generates detailed metrics:
- ⏱️ Duration per step
- 💾 Memory usage
- 📊 Output file sizes
- 🔗 Estimated network calls
- 📈 Bottleneck identification

Results saved to: `pipeline-output/pipeline_performance.json`

## Optimize

After running baseline analysis:

1. **Identify bottleneck**: Which step took longest?

2. **Target optimization**:
   ```
   CATALOG (60s) → Can use incremental updates
   CONSOLIDATE (50s) → Can parallelize table exports
   COLLECT (45s) → Can use async batching
   DASHBOARD (16s) → Can parallelize API calls
   ```

3. **Implement fix** (see LOCAL_TESTING_GUIDE.md)

4. **Measure improvement**:
   ```bash
   bash test_pipeline.sh analyze  # Compare results
   ```

## What to Expect

### First Run (Baseline)
- COLLECT: 10-45s (varies by DJEN server)
- CONSOLIDATE: 5-60s (depends on ZIP availability)
- EMBED: 5-20s (depends on API availability)
- CATALOG: 20-90s (manifests 52K+ records)
- DASHBOARD: 10-20s (API calls)

**Total: 50-250 seconds** (depending on data/connectivity)

### Typical Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| "No ZIPs found" | Backfill queue empty or no complete dates | Use `--date 2026-01-20` instead of `--backfill` |
| "Connection timeout" | DJEN proxy slow | Wait/retry or reduce `--max-items` |
| "IA command failed" | Internet Archive API slow | Retry later or check network |
| "Memory error" | Processing too much data | Use smaller `--max-*` values |

### Example Optimization Flow

```bash
# 1. Baseline
bash test_pipeline.sh analyze
# Result: Total 145s (CATALOG is 60s, CONSOLIDATE is 50s)

# 2. Optimize CATALOG (use incremental updates)
# Edit scripts/catalog/build.py to check last_update_time

# 3. Test improvement
bash test_pipeline.sh catalog
# Now 12s instead of 60s! ✓

# 4. Full pipeline
bash test_pipeline.sh full
# Total now 97s (33% faster!)

# 5. Optimize CONSOLIDATE (parallel exports)
# Edit scripts/pipeline/consolidate.py to use ThreadPoolExecutor

# 6. Test again
bash test_pipeline.sh consolidate
# Now 15s instead of 50s! ✓

# 7. Final full run
bash test_pipeline.sh full
# Total now 52s (64% faster!)
```

## Commands Reference

```bash
# Test pipeline
bash test_pipeline.sh [collect|consolidate|embed|catalog|dashboard|full|analyze|clean]

# Alternative: using Make (requires Linux/Mac)
make -f Makefile.local [help|check|collect|consolidate|embed|catalog|dashboard|full|analyze|clean]

# Run with custom parameters
cd pipeline-output
uv run python ../scripts/pipeline/collect.py --max-items 20 --date 2026-01-20
uv run python ../scripts/pipeline/consolidate.py --backfill --max-zips 10
```

## Files Generated

- `pipeline-output/` - All test data
- `pipeline_performance.json` - Performance metrics
- `*.zip` - Downloaded files
- `*.parquet` - Consolidated data
- `*.duckdb` - Embeddings database
- `*.json`, `*.xml` - Dashboard cache

Clean with: `bash test_pipeline.sh clean`

## Next Steps

1. **Run baseline**: `bash test_pipeline.sh analyze`
2. **Read results**: `cat pipeline-output/pipeline_performance.json | jq .`
3. **Identify slow step**: Look for `duration_sec` > 50
4. **Refer to LOCAL_TESTING_GUIDE.md** for optimization strategies
5. **Implement & measure**: Make changes, re-test, compare

## Troubleshooting

```bash
# Debug credentials
echo $IAS3_ACCESS_KEY $IAS3_SECRET_KEY

# Reload .env
source ../.env

# Check connectivity
curl -s https://archive.org/services/search/v1/scrape?output=json | head

# View logs
tail -f pipeline-output/*.log

# Manual step with debug output
cd pipeline-output
uv run python -v ../scripts/pipeline/collect.py --max-items 2
```

---

**Questions?** Check `LOCAL_TESTING_GUIDE.md` for detailed optimization guide.
