# HTTP relay (STJ / TJRO)

Cloud Run function (gen2, Python 3.12, `southamerica-east1`) that forwards a
single HTTP request to an allowlisted host (`*.stj.jus.br`, `*.tjro.jus.br`).
Exists because GitHub-hosted runners are blocked at the network level for
both sources — STJ's WAF returns 403 for runner IP ranges
(`STJWAFBlockedError`), and TJRO's backend times out connecting from them —
while this function's egress IP is not blocked (validated live, 2026-07-13,
before any of this was built — see the Fase 0 note below).

Serverless platforms don't support proxy `CONNECT`, so the repo routes
through this via a custom httpx transport (`src/common/relay.py`) instead of
`HTTPS_PROXY`: the destination URL travels in an `X-Relay-Url` header, and
the relay forwards method/body/headers to it directly.

## Why this exists (Fase 0)

Before writing any of this, a throwaway `probe` function was deployed to the
same region to confirm serverless egress IPs aren't *also* blocked (Google's
IP ranges are a plausible target too). It made the exact same GET/POST the
real crawlers make and got back real content in both cases (STJ: CKAN JSON;
TJRO: Elasticsearch hits, ~3s). The probe function was deleted immediately
after — it was never part of the relay.

## Deploying

```bash
# One-time: create the shared-secret token (rotate by adding a new version
# and redeploying — the function always reads `:latest`).
openssl rand -base64 32 | tr -d '\n' > /tmp/relay-token.txt
gcloud secrets create relay-token --data-file=/tmp/relay-token.txt
# (or, to rotate an existing secret: gcloud secrets versions add relay-token --data-file=/tmp/relay-token.txt)

gcloud secrets add-iam-policy-binding relay-token \
  --member="serviceAccount:<PROJECT_NUMBER>-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Deploy the relay function.
cd deployment/relay/function
gcloud functions deploy relay \
  --gen2 \
  --runtime=python312 \
  --region=southamerica-east1 \
  --source=. \
  --entry-point=relay \
  --trigger-http \
  --allow-unauthenticated \
  --memory=256Mi \
  --timeout=120s \
  --set-secrets="RELAY_TOKEN=relay-token:latest"
```

`--allow-unauthenticated` is safe here because authorization is enforced by
the application itself (`X-Relay-Token`, constant-time compared) plus the
host allowlist — not by IAM. Rotating to `--no-allow-unauthenticated` +
Workload Identity Federation from GitHub Actions is a reasonable hardening
step later, but wasn't required for this delivery.

## Validating after deploy

```bash
RELAY_URL="$(gcloud functions describe relay --region=southamerica-east1 --gen2 --format='value(serviceConfig.uri)')"
TOKEN="$(gcloud secrets versions access latest --secret=relay-token)"

# STJ — real content, not a WAF challenge page
curl -s -H "X-Relay-Url: https://dadosabertos.web.stj.jus.br/api/3/action/package_show?id=a96a175b-a54b-4bfd-82b8-fcd7cc0200bc" \
     -H "X-Relay-Token: $TOKEN" "$RELAY_URL" | head -c 300

# TJRO — POST, real ES hits
curl -s -H "X-Relay-Url: https://juris-back.tjro.jus.br/search/varios_parametros/" \
     -H "X-Relay-Token: $TOKEN" -H "Content-Type: application/json" \
     -d '{"from":0,"size":1,"fields":{"tipo.raw":["ACÓRDÃO"]},"sort":[{"dtjulgamento":"desc"},{"_score":"desc"},{"id_processo_documento":"asc"}]}' \
     "$RELAY_URL" | head -c 300

# Allowlist rejection — expect 403
curl -s -o /dev/null -w '%{http_code}\n' -H "X-Relay-Url: https://example.com/" -H "X-Relay-Token: $TOKEN" "$RELAY_URL"

# Missing token — expect 401
curl -s -o /dev/null -w '%{http_code}\n' -H "X-Relay-Url: https://dadosabertos.web.stj.jus.br/" "$RELAY_URL"
```

## Cost

Gen2 Cloud Run functions free tier: 2M invocations/month, 360k GB-seconds,
180k vCPU-seconds. At 256Mi/~0.17 vCPU and a few hundred requests/day
(dozens to low hundreds per sync run, well under 1k/day), this stays inside
the free tier by a wide margin — expected cost is $0/month.

## Repo-side wiring

- `src/common/relay.py` — `RelayTransport`/`AsyncRelayTransport`, activated
  by `RELAY_URL`/`RELAY_TOKEN` env vars; falls back to a direct connection
  when either is unset (local/dev default, zero impact).
- `src/stj_acordaos/client.py`, `src/tjro_juris/client.py` — pass
  `transport=relay_transport_from_env()` into their `httpx.Client`.
- `.github/workflows/stj-sync.yml`, `tjro-sync.yml` — `RELAY_URL`/
  `RELAY_TOKEN` (GitHub Secrets) are exported **only** on the
  download/crawl step, never on the IA upload step.
