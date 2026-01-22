# Cloud Functions

This directory contains Google Cloud Functions for CausaGanha infrastructure.

## Functions

### `djen_proxy.py` - DJEN API Proxy

**Purpose**: Bypass geo-blocking on PJe DJEN API by deploying a proxy in Brazil.

**Why**: The DJEN API (`https://comunicaapi.pje.jus.br`) blocks non-Brazilian IPs with `403 Forbidden`. This function runs in Google Cloud's São Paulo region and forwards requests.

**Architecture**:
```
Application → Cloud Function (Brazil) → DJEN API ✓
           (anywhere)    (São Paulo)      (geo-OK)
```

**Deployment**:
```bash
# Quick deploy
cd src/causaganha/infrastructure/cloud/functions
./deploy-djen-proxy.sh

# Manual deploy
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
  --set-env-vars=PROXY_API_KEY=your-random-key
```

**Configuration**:
```bash
# .env
DJEN_PROXY_URL=https://djen-proxy-xxxxx.southamerica-east1.run.app
DJEN_PROXY_API_KEY=your-random-key
```

**Usage**:
```python
from causaganha.v2.api.client import PJeAPIClient

# Automatically uses proxy if DJEN_PROXY_URL is set
client = PJeAPIClient()
intimations = await client.get_intimations_by_court("TJRO")
```

**Testing**:
```bash
# Health check
curl https://your-function-url/health

# API request
curl -H "X-API-Key: your-key" \
  "https://your-function-url/api/v1/comunicacao?siglaTribunal=TJRO&limit=1"
```

**Monitoring**:
```bash
# View logs
gcloud functions logs read djen-proxy --region=southamerica-east1 --limit=50

# Describe function
gcloud functions describe djen-proxy --region=southamerica-east1 --gen2
```

**Cost**: ~$2.50/month (likely free tier for MVP usage)

**Security**:
- API key authentication (X-API-Key header)
- Path whitelist (only /comunicacao endpoint)
- Request/response logging
- CORS enabled for web clients

### Other Functions

- `ingest.py` - PDF download and Internet Archive upload worker
- `llm.py` - LLM analysis worker
- `scheduler.py` - Pipeline orchestration

## Development

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (requires Functions Framework)
pip install functions-framework
functions-framework --target=djen_proxy_handler --debug
```

### Requirements

All functions share `requirements.txt`. Keep dependencies minimal to reduce cold start time.

## Deployment Best Practices

1. **Environment Variables**: Use `--set-env-vars` for secrets (API keys)
2. **Region Selection**: Deploy close to data source (São Paulo for DJEN)
3. **Memory**: Start with 256MB, increase if needed
4. **Timeout**: 60s for external API calls
5. **Monitoring**: Enable Cloud Logging and alerting

## Troubleshooting

**403 Forbidden from DJEN API**:
- Verify function is deployed to `southamerica-east1` (Brazil)
- Check function logs for actual error
- Test directly: `curl https://comunicaapi.pje.jus.br/api/v1/comunicacao?siglaTribunal=TJRO&limit=1`

**401 Unauthorized from Proxy**:
- Check X-API-Key header matches PROXY_API_KEY
- Verify environment variable is set on function

**500 Internal Error**:
- Check function logs: `gcloud functions logs read djen-proxy --region=southamerica-east1`
- Verify requirements.txt dependencies installed
- Check PROXY_API_KEY is configured

**Cold Start Latency**:
- First request may take 1-2s (cold start)
- Subsequent requests <500ms
- Consider keeping function warm with health check pings

## References

- [Cloud Functions Documentation](https://cloud.google.com/functions/docs)
- [DJEN Proxy Implementation Plan](../../../../docs/plans/djen-proxy-cloud-function.md)
- [PJe API Documentation](../../../v2/api/README.md)
