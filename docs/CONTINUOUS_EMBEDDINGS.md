# Continuous Embedding Generation (24/7 High-Throughput)

This document describes the **continuous embedding generation system** for CausaGanha, designed for 24/7 high-throughput processing to cover full tribunal volumes.

## Overview

The continuous system processes embeddings **hourly** (24 runs/day) to achieve near-real-time coverage of all analyzed decisions:

- **Unlimited scale** (GitHub Actions free tier for public repos)
- **High throughput** (20+ concurrent API requests)
- **Automatic caching** (DuckDB persists between runs)
- **Progressive processing** (catches up on backlog, then maintains real-time)
- **Zero cost** (public repository = unlimited Actions minutes)

## Architecture

```
GitHub Actions (Every Hour, 24/7)
    ↓
1. Restore DuckDB cache from previous run
    ↓
2. Query ALL unembedded decisions (no time limit)
    ↓
3. Process up to 1,000 decisions per run
    ↓
4. Generate embeddings (Jina v4, 1024D, 20 concurrent)
    ↓
5. Save to DuckDB (native FLOAT[] arrays)
    ↓
6. Save DuckDB cache for next run
    ↓
7. Once per day (6 AM UTC): Export to Parquet + Upload to IA
```

## Performance Characteristics

### Throughput

**Per Run** (hourly):
- Duration: 45-55 minutes
- Decisions processed: 500-1,000
- Throughput: ~10-20 decisions/minute
- Concurrency: 20 parallel API requests

**Daily Capacity**:
- 24 runs × 750 decisions (average) = **18,000 decisions/day**
- Covers TJRO (2,000/day) with **9x headroom**
- Can scale to medium tribunals (10,000/day) with **1.8x headroom**

### Cost (Public Repository)

```
GitHub Actions (Public Repo):
✅ Unlimited workflow minutes
✅ 10 GB cache storage
✅ Total: $0/month

Jina API:
✅ 18,000 decisions/day × 30 days = 540,000 decisions/month
✅ ~270M tokens/month (500 tokens/decision average)
✅ Free tier: 1M tokens/month
✅ Overage: 269M × $0.02/1M = $5.38/month
✅ Total: ~$5/month

TOTAL COST: ~$5/month
```

## Schedule

The system runs **hourly**:

```
00:00 UTC - Process batch
01:00 UTC - Process batch
02:00 UTC - Process batch
...
06:00 UTC - Process batch + Daily export to Parquet + IA upload
...
23:00 UTC - Process batch
```

**Daily export** happens only at 6 AM UTC to avoid redundant uploads.

## Setup

### 1. Make Repository Public

**Required for unlimited Actions minutes**:

1. Go to repository Settings
2. Scroll to "Danger Zone"
3. Click "Change visibility" → "Make public"
4. Confirm

### 2. Configure GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

```
JINA_API_KEY          # Jina AI API key (already configured)
GOOGLE_API_KEY        # Google AI API key (fallback, optional)
IA_ACCESS_KEY         # Internet Archive access key
IA_SECRET_KEY         # Internet Archive secret key
```

### 3. Enable GitHub Actions

1. Go to repository Settings → Actions → General
2. Enable "Allow all actions and reusable workflows"
3. Enable "Read and write permissions" for GITHUB_TOKEN

### 4. Activate Workflow

The workflow `.github/workflows/continuous-embeddings.yml` will run automatically every hour.

**First run**:
- May take longer as it builds cache
- 0% cache hit rate (normal)

**Subsequent runs**:
- 60-80% cache hit rate
- Faster processing due to caching

## Monitoring

### View Job Status

1. Go to Actions tab
2. Click on latest "Continuous Embedding Generation (24/7)" run
3. View logs for each step

### Check Statistics

Statistics are saved as artifacts:

1. Go to completed workflow run
2. Scroll to "Artifacts" section
3. Download `embedding-stats-XXXXX`
4. View JSON file with metrics

### Example Statistics

```json
{
  "timestamp": "2026-01-21T10:30:45.123456",
  "run_type": "continuous",
  "max_decisions": 1000,
  "max_concurrency": 20,
  "total_decisions": 876,
  "cached_decisions": 124,
  "processed_decisions": 876,
  "failed_decisions": 0,
  "cache_hit_rate": 0.141,
  "success_rate": 1.0,
  "duration_seconds": 2847.32,
  "throughput": 0.308
}
```

## Manual Trigger

You can manually trigger the workflow with custom parameters:

1. Go to Actions tab
2. Select "Continuous Embedding Generation (24/7)"
3. Click "Run workflow"
4. Optionally adjust:
   - `max_decisions`: Max decisions per run (default: 1000)
   - `max_concurrency`: Parallel requests (default: 20)

## Scaling

### Current Configuration (Default)

```yaml
max_decisions: 1000       # Process up to 1,000 per run
max_concurrency: 20       # 20 parallel API requests
timeout_minutes: 55       # Stop 5 min before next run
```

**Capacity**: ~18,000 decisions/day

### Scale to Larger Tribunals

For tribunals with 20,000+ decisions/day, adjust parameters:

```yaml
max_decisions: 2000       # Process more per run
max_concurrency: 30       # More parallel requests
timeout_minutes: 55       # Keep same timeout
```

**New capacity**: ~36,000 decisions/day

**⚠️ Rate Limits**: Jina free tier allows 100 requests/minute. With `max_concurrency=30`, you might hit rate limits. Consider upgrading to Jina paid tier.

## Cache Management

### How Caching Works

- **DuckDB file** saved after each run using GitHub Actions cache
- **Cache key** includes run number for versioning
- **Restore keys** fall back to previous runs
- **Storage**: 10 GB limit (shared across all public repos)

### Expected Cache Hit Rates

- **First run**: 0% (no cache exists)
- **Catching up (backlog)**: 10-30% (mostly new decisions)
- **Steady state**: 60-80% (most decisions already embedded)
- **After analysis surge**: May drop temporarily

### Manual Cache Clear

To force regeneration of all embeddings:

1. Go to Actions tab
2. Click "Caches" in left sidebar
3. Delete cache starting with `embeddings-db-`

## Jina AI Configuration

The system uses **Jina AI embeddings v4**:

```python
Model: jina-embeddings-v4
Dimension: 1024D
Max tokens: 32,000 (supports full legal decisions)
Provider: Jina AI
```

### API Limits

**Free Tier**:
- 1M tokens/month
- 100 requests/minute

**Paid Tier** ($20/month):
- 10M tokens/month
- 300 requests/minute

For high-volume tribunals (20,000+ decisions/day), consider upgrading to paid tier.

## Troubleshooting

### Job Failed

**Check logs**:
1. Go to failed workflow run
2. Click on failed step
3. Read error message

**Common issues**:

1. **Rate limit exceeded (429 error)**
   - Solution: Reduce `max_concurrency` from 20 → 10
   - Or upgrade to Jina paid tier

2. **Timeout (job exceeds 55 minutes)**
   - Solution: Reduce `max_decisions` from 1000 → 500
   - Means more frequent runs, but each completes faster

3. **API key invalid**
   - Solution: Verify GitHub secret `JINA_API_KEY` is set correctly
   - Test: Run manual workflow with verbose logging

4. **Cache restore failed**
   - Solution: Normal for first run
   - Subsequent runs will work

5. **No decisions to process**
   - Solution: Normal if caught up
   - System will idle until new decisions analyzed

### Performance Issues

**Job too slow (>50 minutes)**:
- Increase `max_concurrency` (but watch rate limits)
- Check cache hit rate (should be >60% in steady state)
- Verify DuckDB cache is being restored

**Job too fast (<10 minutes, suspicious)**:
- Check actual decisions processed
- Verify cache hit rate is reasonable
- Ensure decisions are being embedded, not just cached

**Low throughput (<5 decisions/minute)**:
- Check API latency (Jina should be <200ms/request)
- Verify concurrency is working (20 parallel requests)
- Check for network issues or rate limiting

## Development

### Run Locally

```bash
# Set environment variables
export JINA_API_KEY="your_key"
export GOOGLE_API_KEY="your_key"  # Optional fallback

# Run continuous job (process 100 decisions)
uv run python scripts/continuous_embedding_job.py \
    --max-decisions 100 \
    --max-concurrency 10 \
    --timeout-minutes 30

# Check statistics
cat data/stats/continuous_*.json | jq
```

### Test Workflow Locally

```bash
# Install act (GitHub Actions local runner)
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run workflow locally
act schedule -j generate-embeddings
```

## Comparison: Daily vs Continuous

| Metric | Daily System | Continuous System (24/7) |
|--------|-------------|--------------------------|
| **Frequency** | Once/day (3 AM) | Hourly (24 runs/day) |
| **Capacity** | ~5,000 decisions/day | ~18,000 decisions/day |
| **Latency** | Up to 24 hours | Up to 1 hour |
| **Cost (public repo)** | $0/month | $0/month |
| **Cost (private repo)** | $0-$6/month | $156/month ⚠️ |
| **Use case** | Low-volume tribunals | Full tribunal coverage |

## Migration from Daily to Continuous

If you're switching from daily to continuous:

1. **Disable daily workflow**:
   ```bash
   # Rename to disable
   mv .github/workflows/daily-embeddings.yml \
      .github/workflows/daily-embeddings.yml.disabled
   ```

2. **Enable continuous workflow**:
   - Already enabled at `.github/workflows/continuous-embeddings.yml`

3. **Wait for first run**:
   - First run will process backlog (may take full 55 minutes)
   - Subsequent runs will be faster

4. **Monitor for 24 hours**:
   - Check that runs complete successfully
   - Verify cache hit rate increases
   - Ensure no rate limit errors

## Future Improvements

Potential enhancements:

1. **Dynamic concurrency** - Adjust based on rate limit headroom
2. **Smart scheduling** - Skip runs when no new decisions
3. **Multi-tribunal processing** - Parallel workflows per tribunal
4. **Adaptive timeout** - Adjust based on remaining decisions
5. **Quality monitoring** - Track embedding quality over time

## Support

For issues or questions:
- **GitHub Issues**: https://github.com/franklinbaldo/causaganha/issues
- **Workflow Logs**: Actions tab in GitHub repository
- **Documentation**: This file and inline code comments
- **Statistics**: Download artifacts from completed runs

## Summary

The continuous embedding system provides:

✅ **24/7 processing** with hourly runs
✅ **High throughput** (~18,000 decisions/day)
✅ **Zero cost** for public repositories
✅ **Automatic caching** (60-80% hit rate)
✅ **Progressive processing** (catches up, then maintains)
✅ **Full tribunal coverage** with headroom to scale

**For private repos**: Consider daily system or Cloud Run deployment to avoid high Actions costs ($156/month).

**For public repos**: Unlimited and free! 🎉
