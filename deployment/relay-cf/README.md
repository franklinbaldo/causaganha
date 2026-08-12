# Cloudflare relay probe

Authenticated, allowlisted HTTP relay used to test a Cloudflare egress path
when the existing GCP relay cannot reach TJRO JURIS. It preserves the same
`X-Relay-Url` / `X-Relay-Token` contract consumed by `src/common/relay.py`.

This is deliberately a probe, not an open proxy:

- only `GET`, `HEAD`, and `POST` are accepted;
- only HTTPS subdomains of `stj.jus.br` and `tjro.jus.br` are reachable;
- redirects are returned to the caller and never followed by the Worker;
- relay, forwarding, Cloudflare, and hop-by-hop headers are removed;
- request and response bodies are streamed;
- the token lives only in the `RELAY_TOKEN` Worker secret.

## Probe result

On 2026-08-11 the hardened Worker was deployed as `tjro-relay-probe`
(version `5565f2a5-9740-4c54-9c7f-d8856341d601`). A bounded POST to the JURIS
search endpoint reached TJRO but returned the HTML page `STIC - Página
Bloqueada`. A second bounded probe from a temporary Google Cloud Function in
`us-central1` produced the same result; that temporary function was then
deleted.

Therefore this Worker is **not** an operational TJRO relay and must not be
wired into the `RELAY_URL` GitHub secret. The GitHub-hosted dry-run below
remains the acceptance gate for any future egress provider.

## Validate and deploy

```bash
npm ci
npm test
npm run check
npx wrangler whoami
npx wrangler secret put RELAY_TOKEN
npm run deploy
```

After deployment, test one bounded JURIS query before changing GitHub Actions
secrets. The decisive acceptance test is a manually dispatched `TJRO Sync`
from a GitHub-hosted runner with `skip_upload=true`, one month, and one type.

Never commit `.dev.vars`, `.wrangler/`, or a relay token.
