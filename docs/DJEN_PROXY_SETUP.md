# DJEN API Proxy Setup Guide

## Overview

The PJe DJEN API (`https://comunicaapi.pje.jus.br`) implements geo-blocking and returns `403 Forbidden` when accessed from non-Brazilian IP addresses. This proxy solution bypasses the restriction by deploying a Google Cloud Function in São Paulo, Brazil.

## Quick Start

### Option 1: Interactive Wizard (Recommended)

Run the interactive setup wizard:

```bash
./scripts/setup-djen-proxy-wizard.sh
```

The wizard will guide you through:
1. Prerequisites check (gcloud CLI)
2. Google Cloud project configuration
3. Authentication mode selection
4. Function deployment
5. Local configuration
6. Testing

### Option 2: Manual Setup

```bash
cd src/causaganha/infrastructure/cloud/functions
./deploy-djen-proxy.sh
```

Then add to `.env`:
```bash
DJEN_PROXY_URL=https://djen-proxy-xxxxx.southamerica-east1.run.app
```

## Architecture

```
┌──────────────┐         ┌─────────────────────┐         ┌────────────┐
│ CausaGanha   │ HTTPS   │ Cloud Function      │ HTTPS   │ DJEN API   │
│ Application  ├────────►│ (São Paulo)         ├────────►│ (Brazil)   │
│ (anywhere)   │         │ southamerica-east1  │         │ Geo-OK ✓   │
└──────────────┘         └─────────────────────┘         └────────────┘
```

## Authentication Modes

### Public Access (Default - Recommended)

**Use when:** Personal development, MVP, team usage

```bash
# Deploy without authentication
REQUIRE_AUTH=false ./deploy-djen-proxy.sh
```

**Pros:**
- Simple to use
- No API key management
- DJEN data is public anyway

**Cons:**
- Anyone with the URL can use it
- No usage control

### Protected Access

**Use when:** Production, public deployment, cost control needed

```bash
# Deploy with authentication
REQUIRE_AUTH=true PROXY_API_KEY=your-random-key ./deploy-djen-proxy.sh
```

**Pros:**
- Prevent unauthorized usage
- Usage control
- Cost protection

**Cons:**
- Need to manage API key
- Extra configuration

## Configuration

### Environment Variables

```bash
# Required
DJEN_PROXY_URL=https://djen-proxy-xxxxx.southamerica-east1.run.app

# Optional (only if using protected mode)
DJEN_PROXY_API_KEY=your-random-api-key
```

### GitHub Secrets

For CI/CD, add secrets to GitHub:

```bash
gh secret set DJEN_PROXY_URL --body="https://..."
gh secret set DJEN_PROXY_API_KEY --body="..."
```

## Usage

### Automatic (Recommended)

The `PJeAPIClient` automatically detects and uses the proxy:

```python
from causaganha.v2.api.client import PJeAPIClient

# Automatically uses proxy if DJEN_PROXY_URL is set
client = PJeAPIClient()
intimations = await client.get_intimations_by_court("TJRO")
```

### Manual Control

```python
# Force proxy usage
client = PJeAPIClient(use_proxy=True)

# Force direct connection (no proxy)
client = PJeAPIClient(use_proxy=False)
```

## Testing

### 1. Health Check

```bash
# Public mode
curl https://your-function-url/health

# Protected mode
curl -H "X-API-Key: your-key" https://your-function-url/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "djen-proxy",
  "auth_required": false,
  "region": "southamerica-east1"
}
```

### 2. API Request

```bash
# Public mode
curl "https://your-function-url/api/v1/comunicacao?siglaTribunal=TJRO&limit=1"

# Protected mode
curl -H "X-API-Key: your-key" \
  "https://your-function-url/api/v1/comunicacao?siglaTribunal=TJRO&limit=1"
```

### 3. Python Test

```bash
uv run python experiments/test_djen_api.py
```

Should now show successful connection instead of 403!

## Monitoring

### View Logs

```bash
gcloud functions logs read djen-proxy \
  --region=southamerica-east1 \
  --limit=50
```

### Function Status

```bash
gcloud functions describe djen-proxy \
  --region=southamerica-east1 \
  --gen2
```

### Metrics

Visit Google Cloud Console:
- Functions → djen-proxy → Metrics
- Monitor: Invocations, Errors, Latency, Cost

## Cost

### Pricing

| Component | Price | Typical Usage | Cost/Month |
|-----------|-------|---------------|------------|
| Invocations | $0.40/million | 100K | $0.04 |
| Compute (256MB) | $0.0000025/100ms | 5s avg | $1.25 |
| Egress | $0.12/GB | 10GB | $1.20 |
| **Total** | | | **~$2.50** |

### Free Tier

- 2 million invocations/month
- 400,000 GB-seconds compute
- MVP usage likely covered entirely by free tier

### Cost Optimization

1. **Cache responses** (future enhancement)
2. **Batch requests** when possible
3. **Set billing alerts** at $5, $10, $25
4. **Monitor usage** weekly

## Troubleshooting

### Still Getting 403

**Cause:** Function not deployed to Brazil region

**Fix:**
```bash
# Verify region
gcloud functions describe djen-proxy --gen2 --format="value(serviceConfig.uri)"
# Should include "southamerica-east1"
```

### 401 Unauthorized

**Cause:** Missing or wrong API key (protected mode)

**Fix:**
```bash
# Check environment
echo $DJEN_PROXY_API_KEY

# Update .env
DJEN_PROXY_API_KEY=correct-key
```

### Function Not Found

**Cause:** Not deployed yet

**Fix:**
```bash
cd src/causaganha/infrastructure/cloud/functions
./deploy-djen-proxy.sh
```

### Slow Response Times

**Cause:** Cold start (first request after idle)

**Solution:**
- First request: ~1-2s (cold start)
- Subsequent requests: <500ms
- Keep warm with periodic health checks

### High Costs

**Cause:** Unexpected high usage

**Fix:**
1. Check logs for abuse
2. Enable authentication (`REQUIRE_AUTH=true`)
3. Add rate limiting (custom implementation)
4. Set up billing alerts

## Security

### Best Practices

1. **API Key Rotation** (protected mode)
   - Rotate quarterly
   - Use strong random keys: `openssl rand -base64 32`
   - Store in GitHub Secrets

2. **Access Logging**
   - All requests logged to Cloud Logging
   - Monitor for unusual patterns
   - Set up alerts for high error rates

3. **CORS**
   - Currently allows all origins (`*`)
   - Restrict if needed for web apps

4. **Path Whitelist**
   - Only `/comunicacao` and `/health` allowed
   - Prevents proxy abuse

## Alternatives

If you can't use Google Cloud Functions:

1. **Tailscale Exit Node** (already documented)
   - Set up Tailscale with Brazil exit node
   - More complex setup

2. **VPN Service**
   - Use commercial Brazil VPN
   - Ongoing cost, reliability concerns

3. **AWS Lambda** (São Paulo region)
   - Similar to Cloud Functions
   - Use `us-east-1` region

## FAQ

**Q: Why not just use a VPN?**
A: VPNs require manual setup on each machine. This solution works automatically for the whole team and in CI/CD.

**Q: Is this legal?**
A: Yes. The DJEN API serves public court records. We're just bypassing a technical geo-fence, not accessing private data.

**Q: What if Google Cloud is too expensive?**
A: The free tier covers MVP usage entirely. For production, consider caching or Tailscale.

**Q: Can I deploy multiple proxies?**
A: Yes! Deploy to different regions for redundancy or change the function name.

**Q: Does this work for other geo-blocked APIs?**
A: Yes, with modifications. Change the `DJEN_BASE_URL` and deploy to the appropriate region.

## Support

- **Documentation:** `/docs/plans/djen-proxy-cloud-function.md`
- **Code:** `/src/causaganha/infrastructure/cloud/functions/`
- **Issues:** Report via GitHub Issues

## References

- [Google Cloud Functions Documentation](https://cloud.google.com/functions/docs)
- [DJEN Implementation Plan](plans/djen-proxy-cloud-function.md)
- [PJe API Client](../src/causaganha/v2/api/client.py)
- [Compliance Guidelines](COMPLIANCE.md)
