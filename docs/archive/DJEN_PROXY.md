# DJEN Proxy

## Overview

The DJEN API (comunicaapi.pje.jus.br) is **geo-blocked to Brazilian IPs only**. To enable global access for our GitHub Actions pipelines, we run a reverse proxy on Google Cloud Run in the São Paulo region.

## Why We Need It

```
GitHub Actions (US servers) ──✗──▶ DJEN API (geo-blocked)
                                     │
GitHub Actions ──────────────────────▶ DJEN Proxy (São Paulo) ──▶ DJEN API ✓
```

Without the proxy:
- GitHub Actions runners are in the US
- DJEN API returns 403 Forbidden for non-Brazilian IPs
- Our automated pipelines would fail

## Proxy Details

| Property | Value |
|----------|-------|
| **URL** | `https://djen-proxy-mhgmawcn3a-rj.a.run.app` |
| **Region** | `southamerica-east1` (São Paulo, Brazil) |
| **Platform** | Google Cloud Run |
| **Language** | Go 1.21 |
| **Cost** | $0/month (free tier) |
| **Source** | `djen_proxy.go` (32 lines) |

## Allowed Paths

For security, the proxy only forwards requests to specific paths:

| Path Pattern | Purpose |
|--------------|---------|
| `/api/*` | DJEN REST API |
| `/swagger/*` | API documentation |
| `/comunicacao*` | Communication endpoints |
| `/login*` | Authentication |
| `/health` | Health check |
| `/security` | Security status |

All other paths return **403 Forbidden**.

## Usage

```bash
# Direct API call (blocked outside Brazil)
curl https://comunicaapi.pje.jus.br/api/v1/caderno/TJRO/2026-01-15/D
# Error: 403 Forbidden

# Via proxy (works globally)
curl https://djen-proxy-mhgmawcn3a-rj.a.run.app/api/v1/caderno/TJRO/2026-01-15/D
# Success: Returns JSON
```

## In GitHub Actions

The proxy URL is configured in `pipeline.yml`:

```yaml
# .github/workflows/pipeline.yml
env:
  DJEN_PROXY_URL: https://djen-proxy-mhgmawcn3a-rj.a.run.app
```

## Deployment

To deploy or update the proxy:

```bash
# Deploy script
./DEPLOY_DJEN_V4.sh

# Or manually
gcloud run deploy djen-proxy \
  --source . \
  --region southamerica-east1 \
  --allow-unauthenticated
```

## Security

- **No authentication required** (public proxy)
- **Path whitelist** prevents abuse
- **Rate limiting** inherited from DJEN API
- **No data stored** (stateless proxy)

## Monitoring

Check proxy health:

```bash
curl https://djen-proxy-mhgmawcn3a-rj.a.run.app/health
```

Run security tests:

```bash
./TEST_DJEN_SECURITY.sh
```

## Alternatives

If the proxy is unavailable:

1. **Tailscale Exit Node**: Route traffic through a Brazilian VPS
2. **Local Development**: Use a Brazilian VPN
3. **Cloud Function**: Deploy equivalent in any Brazilian cloud region

## Related Files

- `djen_proxy.go` - Proxy source code
- `DEPLOY_DJEN_V4.sh` - Deployment script
- `TEST_DJEN_SECURITY.sh` - Security test suite
- `DJEN_INFRASTRUCTURE.md` - Full infrastructure documentation
