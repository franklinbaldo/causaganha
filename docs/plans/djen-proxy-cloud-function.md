# DJEN API Proxy - Cloud Function Implementation Plan

## Problem Statement

The PJe DJEN API (`https://comunicaapi.pje.jus.br`) implements geo-blocking and returns `403 Forbidden` when accessed from non-Brazilian IP addresses. This prevents CausaGanha from accessing judicial data when running outside Brazil.

## Solution: Google Cloud Function Proxy in Brazil

Deploy a lightweight HTTP proxy as a Google Cloud Function in the São Paulo region (`southamerica-east1`) to forward requests to the DJEN API.

### Architecture

```
┌──────────────┐         ┌─────────────────────┐         ┌────────────┐
│ CausaGanha   │ HTTPS   │ Cloud Function      │ HTTPS   │ DJEN API   │
│ Application  ├────────►│ (São Paulo)         ├────────►│ (Brazil)   │
│ (anywhere)   │         │ southamerica-east1  │         │ Geo-OK ✓   │
└──────────────┘         └─────────────────────┘         └────────────┘
```

### Key Features

1. **Geo-Bypass**: Function deployed in Brazil region has Brazilian IP
2. **Lightweight**: Simple HTTP proxy, no data storage
3. **Secure**: API key authentication to prevent abuse
4. **Rate Limited**: Respect DJEN API limits
5. **Cost Effective**: Pay only for actual usage
6. **Auto-Scaling**: Handles traffic spikes automatically

## Implementation Steps

### 1. Cloud Function (`functions/djen_proxy.py`)

**Purpose**: Receive requests, forward to DJEN API, return response

**Features**:
- API key authentication
- Request/response logging
- Error handling
- Rate limiting
- CORS support (if needed)

### 2. Deployment Configuration

**Region**: `southamerica-east1` (São Paulo, Brazil)
**Runtime**: Python 3.12
**Memory**: 256 MB
**Timeout**: 60s
**Trigger**: HTTPS
**Authentication**: API key in custom header

### 3. Client Update

Update `PJeAPIClient` to support proxy mode:
- Environment variable: `DJEN_PROXY_URL`
- Automatic proxy detection
- API key injection

### 4. Security Considerations

**API Key Protection**:
- Store in GitHub Secrets
- Rotate periodically
- Monitor usage

**Rate Limiting**:
- Respect DJEN API limits
- Implement client-side throttling
- Monitor quota usage

**Compliance** (from `docs/COMPLIANCE.md`):
✅ Data is public (court records)
✅ Proper attribution (cite tribunal sources)
✅ Rate limiting (respect API limits)
✅ Reasonable use (daily collection, not aggressive scraping)

### 5. Cost Estimation

**Google Cloud Functions Pricing** (São Paulo region):

| Component | Price | Estimated Usage | Cost/Month |
|-----------|-------|-----------------|------------|
| Invocations | $0.40/million | 100K requests | $0.04 |
| Compute Time (256MB) | $0.0000025/100ms | 5s avg × 100K | $1.25 |
| Egress | $0.12/GB | 10GB | $1.20 |
| **Total** | | | **~$2.50/month** |

**Free Tier** (first 2 million invocations/month):
- MVP usage likely covered by free tier
- Scale cost only applies at production volumes

## Deployment Instructions

### Prerequisites

```bash
# Install Google Cloud SDK
# See: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

### Deploy Function

```bash
# Deploy to São Paulo region
cd src/causaganha/infrastructure/cloud/functions
gcloud functions deploy djen-proxy \
  --gen2 \
  --runtime=python312 \
  --region=southamerica-east1 \
  --source=. \
  --entry-point=djen_proxy_handler \
  --trigger-http \
  --allow-unauthenticated \
  --memory=256MB \
  --timeout=60s \
  --set-env-vars=PROXY_API_KEY=YOUR_RANDOM_KEY

# Get function URL
gcloud functions describe djen-proxy \
  --region=southamerica-east1 \
  --format='value(serviceConfig.uri)'
```

### Configure Application

```bash
# Add to .env
DJEN_PROXY_URL=https://djen-proxy-xxxxx.southamerica-east1.run.app
DJEN_PROXY_API_KEY=YOUR_RANDOM_KEY

# Add to GitHub Secrets
gh secret set DJEN_PROXY_URL --body="https://..."
gh secret set DJEN_PROXY_API_KEY --body="..."
```

## Testing

### 1. Test Proxy Directly

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://YOUR-FUNCTION-URL/api/v1/comunicacao?siglaTribunal=TJRO&limit=1"
```

### 2. Test with Client

```python
import asyncio
from causaganha.v2.api.client import PJeAPIClient

async def test():
    # Auto-detects proxy from env vars
    client = PJeAPIClient()
    intimations = await client.get_intimations_by_court("TJRO", limit_per_page=10)
    print(f"Retrieved {len(intimations)} intimations via proxy")

asyncio.run(test())
```

### 3. Run Experiment

```bash
uv run python experiments/test_djen_api.py
# Should now succeed instead of 403!
```

## Monitoring & Maintenance

### Cloud Monitoring

```bash
# View function logs
gcloud functions logs read djen-proxy \
  --region=southamerica-east1 \
  --limit=50

# Monitor metrics
gcloud monitoring dashboards list
```

### Alerts

Set up alerts for:
- High error rate (>5%)
- High latency (>5s p95)
- Quota approaching limits
- Unusual traffic patterns

### Maintenance

- **Weekly**: Check error logs
- **Monthly**: Review costs and usage
- **Quarterly**: Rotate API key
- **As needed**: Update Python runtime

## Alternatives Considered

| Alternative | Pros | Cons | Verdict |
|-------------|------|------|---------|
| **Cloud Function** ✓ | Serverless, cheap, auto-scale | Small cold start | **Selected** |
| Tailscale Exit Node | Already documented | Requires manual setup | Backup option |
| Cloud Run | More control | More expensive | Overkill |
| VM in Brazil | Full control | High cost, maintenance | Too expensive |
| VPN Service | Simple | Ongoing cost, reliability | Not sustainable |

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Function goes down | High | Health check + alerting |
| API key leaked | High | Rotation + monitoring |
| Cost overrun | Medium | Billing alerts + quotas |
| DJEN blocks function IP | Medium | Deploy multiple regions |
| Compliance concerns | Low | Public data, proper attribution |

## Success Criteria

✅ DJEN API accessible from anywhere
✅ Response time <2s (proxy overhead <500ms)
✅ Monthly cost <$10 for MVP usage
✅ 99.9% uptime
✅ No security incidents
✅ Compliant with DJEN terms of service

## Future Enhancements

**Phase 2**:
- Caching layer (Redis) to reduce DJEN calls
- Request batching for efficiency
- Advanced rate limiting (token bucket)
- Multi-region deployment for redundancy

**Phase 3**:
- Custom domain (api.causaganha.com)
- OAuth authentication
- Usage analytics dashboard
- Automated failover

---

**Status**: Ready for Implementation
**Estimated Effort**: 4 hours (coding + testing + deployment)
**Cost**: ~$2.50/month (likely free tier)
**Risk Level**: Low
