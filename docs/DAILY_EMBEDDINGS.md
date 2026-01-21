# Daily Embedding Generation with GitHub Actions

This document describes the automated daily embedding generation system for CausaGanha.

## Overview

The system automatically generates embeddings for analyzed decisions every day using GitHub Actions. It's optimized for daily digest processing with:

- **Zero cost** (GitHub Actions free tier)
- **Automatic caching** (DuckDB persists between runs)
- **Incremental processing** (only new decisions)
- **Internet Archive upload** (long-term storage)

## Architecture

```
GitHub Actions (Daily at 3 AM Brazil time)
    ↓
1. Restore DuckDB cache from previous run
    ↓
2. Find decisions analyzed in last 24h without embeddings
    ↓
3. Generate embeddings (Jina v4, 1024D)
    ↓
4. Save to DuckDB (native FLOAT[] arrays)
    ↓
5. Export to Parquet (ZSTD compressed)
    ↓
6. Upload to Internet Archive
    ↓
7. Save DuckDB cache for next run
```

## Schedule

- **Runs daily at**: 3 AM Brazil time (6 AM UTC)
- **Processes**: Last 24 hours of analyzed decisions
- **Duration**: ~30-90 minutes (depending on volume)
- **Concurrency**: 10 parallel API requests

## Setup

### 1. Configure GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

```
JINA_API_KEY          # Jina AI API key
GOOGLE_API_KEY        # Google AI API key (fallback)
IA_ACCESS_KEY         # Internet Archive access key
IA_SECRET_KEY         # Internet Archive secret key
```

### 2. Enable GitHub Actions

1. Go to repository Settings → Actions → General
2. Enable "Allow all actions and reusable workflows"
3. Enable "Read and write permissions" for GITHUB_TOKEN

### 3. Verify Workflow

The workflow is defined in `.github/workflows/daily-embeddings.yml` and runs automatically.

## Manual Trigger

You can manually trigger the workflow:

1. Go to Actions tab in GitHub
2. Select "Daily Embedding Generation"
3. Click "Run workflow"
4. Optionally specify `days_back` (default: 1)

## Monitoring

### View Job Status

1. Go to Actions tab
2. Click on latest "Daily Embedding Generation" run
3. View logs for each step

### Check Statistics

Job statistics are saved as artifacts:

1. Go to completed workflow run
2. Scroll to "Artifacts" section
3. Download `embedding-stats-XXXXX`
4. View JSON file with metrics

### Example Statistics

```json
{
  "timestamp": "2026-01-21T06:30:45.123456",
  "days_back": 1,
  "max_concurrency": 10,
  "total_decisions": 1234,
  "cached_decisions": 856,
  "processed_decisions": 1234,
  "failed_decisions": 0,
  "cache_hit_rate": 0.694,
  "success_rate": 1.0,
  "duration_seconds": 2145.67,
  "throughput": 0.575
}
```

## Cache Management

### How Caching Works

- **DuckDB file** is saved after each run using GitHub Actions cache
- **Cache key** includes run number to maintain history
- **Restore keys** fall back to previous runs if exact match not found
- **Storage limit**: 10 GB per repository (plenty for embeddings)

### Cache Hit Rate

Expected cache hit rates:
- **First run**: 0% (no cache)
- **Steady state**: 60-80% (decisions already embedded)
- **After API changes**: May drop temporarily

### Manual Cache Clear

To clear the cache (force regeneration):

1. Go to Actions tab
2. Click "Caches" in left sidebar
3. Delete cache starting with `embeddings-db-`

## Cost Analysis

### GitHub Actions (Free Tier)

```
Public Repository:
✅ Unlimited minutes
✅ 10 GB cache storage
✅ No cost

Daily Usage:
- Runtime: ~30-90 minutes/day
- Cache storage: ~500 MB (DuckDB)
- Total: $0/month
```

### API Costs (Jina AI)

```
Free Tier:
- 1M tokens/month
- 100 requests/minute

Estimated Usage (1,000 decisions/day):
- 30,000 decisions/month
- ~15M tokens/month
- Cache hit rate: 70%
- Actual API calls: ~4.5M tokens/month

Exceeds free tier → Need to monitor
```

### Internet Archive

```
Free:
✅ Unlimited storage
✅ Unlimited bandwidth
✅ No cost
```

## Troubleshooting

### Job Failed

**Check logs**:
1. Go to failed workflow run
2. Click on failed step
3. Read error message

**Common issues**:

1. **Rate limit exceeded** (429 error)
   - Solution: Reduce `max_concurrency` in workflow file
   - Change from 10 → 5 concurrent requests

2. **API key invalid**
   - Solution: Verify GitHub secrets are set correctly

3. **Cache restore failed**
   - Solution: Normal for first run, will work on subsequent runs

4. **No decisions to process**
   - Solution: Normal if no new decisions were analyzed

### Performance Issues

**Job too slow**:
- Increase `max_concurrency` (but watch rate limits)
- Check cache hit rate (should be >60%)
- Verify DuckDB cache is being restored

**Job too fast (suspicious)**:
- Check that decisions are actually being processed
- Verify cache hit rate is reasonable

## Development

### Run Locally

```bash
# Set environment variables
export JINA_API_KEY="your_key"
export GOOGLE_API_KEY="your_key"
export IA_ACCESS_KEY="your_key"
export IA_SECRET_KEY="your_key"

# Run daily job (last 1 day)
uv run python scripts/daily_embedding_job.py --days-back 1

# Export to Parquet
uv run python scripts/export_daily_embeddings.py \
    --output data/exports/test.parquet

# Upload to IA (test)
uv run python scripts/upload_to_ia.py \
    --file data/exports/test.parquet
```

### Test Workflow

```bash
# Install act (GitHub Actions local runner)
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run workflow locally
act schedule -j generate-embeddings
```

## Optimization Tips

### 1. Reduce API Costs

- Enable caching (already done ✅)
- Use batch processing (already done ✅)
- Monitor cache hit rate
- Consider upgrading to Jina paid tier if needed

### 2. Improve Performance

- Increase `max_concurrency` if not hitting rate limits
- Use faster embedding model (trade-off: quality)
- Process only critical decisions daily

### 3. Reduce Storage

- Export only recent embeddings (not full history)
- Increase Parquet compression level (slower, smaller)
- Clean up old artifacts regularly

## Maintenance

### Monthly Checklist

- [ ] Check job success rate (should be >95%)
- [ ] Monitor cache hit rate (should be >60%)
- [ ] Review API usage (watch for overage)
- [ ] Verify IA uploads are successful
- [ ] Clean up old workflow runs (optional)

### Quarterly Review

- [ ] Evaluate embedding model (newer versions?)
- [ ] Review processing schedule (still daily?)
- [ ] Check storage usage (DuckDB size)
- [ ] Optimize concurrency settings

## Future Improvements

Potential enhancements:

1. **Parallel batches** - Split into 5 parallel jobs
2. **Smart scheduling** - Skip weekends if no new data
3. **Incremental IA uploads** - Upload only changed data
4. **Quality monitoring** - Track embedding quality metrics
5. **Auto-scaling** - Adjust concurrency based on rate limits

## Support

For issues or questions:
- **GitHub Issues**: https://github.com/franklinbaldo/causaganha/issues
- **Workflow Logs**: Actions tab in GitHub repository
- **Documentation**: This file and inline code comments
