# Archive.org CORS proxy

Cloudflare Worker that adds `Access-Control-Allow-Origin` to Internet
Archive file downloads so DuckDB-WASM's `httpfs` extension can
`read_parquet()` them directly from the browser.

## Why this exists

`archive.org/metadata/{item}/files` and `archive.org/advancedsearch.php`
send `Access-Control-Allow-Origin`, but `archive.org/download/{item}/{file}`
(which redirects to an `ia*.us.archive.org` node) does not. A cross-origin
`fetch` against the download endpoint is rejected by the browser before
`web/src/components/DuckDBExplorer.svelte` ever sees a response — see
issue #1482. This Worker is the "proxy through the dashboard's own origin"
workaround suggested in that issue: it fetches the file server-side (no
CORS involved between two servers) and re-serves it with the header added.

It is deliberately narrow, not an open proxy:

- only `GET`, `HEAD` and CORS-preflight `OPTIONS` are accepted;
- only paths shaped `/download/{item}/{file}` are forwarded, where `item`
  must start with `djen-` (this project's own dataset naming convention,
  `djen-{tribunal}-{year}`) and `file` must end in `.parquet` — nothing
  else on `archive.org` is reachable through this Worker;
- `Range` is forwarded upstream and `Content-Range`/`Accept-Ranges` are
  preserved in the response, so DuckDB-WASM's partial-read strategy keeps
  working;
- no secrets, no write access, no state — it only re-serves public,
  already-published CausaGanha datasets.

## Validate and deploy

```bash
npm ci
npm test
npm run check
npx wrangler whoami
npm run deploy
```

Once deployed, point `DuckDBExplorer.svelte` at the Worker's URL (see
`web/src/lib/archiveProxyBase.ts`) instead of `archive.org` directly, and
confirm one real query against a live dataset before relying on it.

Never commit `.dev.vars`, `.wrangler/`, or Cloudflare credentials.
