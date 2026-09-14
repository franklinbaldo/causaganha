#!/usr/bin/env node
// Real-browser CORS probe for issue #1471/#1472's "real Archive read-back
// proof" requirement.
//
// DuckDBExplorer.svelte runs `read_parquet('https://archive.org/download/
// {item}/{file}.parquet')` through DuckDB-WASM's httpfs extension directly
// in the browser tab -- a real cross-origin `fetch` from whatever origin
// the dashboard is served from (e.g. a Cloudflare Pages domain) to
// archive.org. It also does a plain `fetch('https://archive.org/metadata/
// {id}/files')` to check dataset existence first. Neither call has ever
// been exercised against the real archive.org host in a real browser by
// this repo's test suite (both DuckDBExplorer.svelte test files mock
// `global.fetch` and the DuckDB connection under Vitest/jsdom).
//
// This probe answers, with an actual Chromium page (not curl, not Node's
// fetch, which do not enforce CORS the way a browser does): does a
// cross-origin `fetch` with a Range header against archive.org's file
// *download* endpoint (`/download/{item}/{file}`, served by a
// `ia*.us.archive.org` datanode) succeed, the way it does for the
// `/metadata/` API endpoint used as this probe's positive control?
//
// Usage:
//   node scripts/benchmarks/archive_cors_probe.mjs \
//     --item djen-tjro-2026 --file comunicacoes.parquet \
//     --origin https://example.org
import { createRequire } from "node:module";
import http from "node:http";

const require = createRequire(import.meta.url);
const { chromium } = require(
  require.resolve("playwright", { paths: ["/opt/node22/lib/node_modules"] })
);

function parseArgs(argv) {
  const args = { item: "djen-tjro-2026", file: "comunicacoes.parquet", origin: "https://cors-probe.invalid" };
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (key === "--item") args.item = argv[++i];
    else if (key === "--file") args.file = argv[++i];
    else if (key === "--origin") args.origin = argv[++i];
  }
  return args;
}

// The probe page must itself be served over HTTP (not opened as a `file://`
// document) so its Origin header is a real cross-origin value the browser
// sends on outgoing fetches -- `file://` pages have an opaque/null origin
// that behaves differently under CORS than a real HTTP(S) origin like the
// production dashboard's.
function serveBlankPage() {
  return new Promise((resolve) => {
    const server = http.createServer((_req, res) => {
      res.writeHead(200, { "Content-Type": "text/html" });
      res.end("<!doctype html><title>cors-probe</title>");
    });
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      resolve({ server, url: `http://127.0.0.1:${port}/` });
    });
  });
}

async function probeFetch(page, url, init) {
  return page.evaluate(
    async ({ url, init }) => {
      try {
        const response = await fetch(url, init);
        const body = await response.arrayBuffer();
        return {
          ok: true,
          status: response.status,
          type: response.type,
          bodyBytes: body.byteLength,
        };
      } catch (error) {
        return { ok: false, errorName: error.name, errorMessage: String(error.message ?? error) };
      }
    },
    { url, init }
  );
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const { server, url: pageUrl } = await serveBlankPage();

  const proxyServer = process.env.HTTPS_PROXY || process.env.https_proxy;
  const browser = await chromium.launch(proxyServer ? { proxy: { server: proxyServer } } : {});
  try {
    const page = await browser.newPage();
    await page.goto(pageUrl);

    const metadataUrl = `https://archive.org/metadata/${args.item}/files`;
    const downloadUrl = `https://archive.org/download/${args.item}/${args.file}`;

    const metadataResult = await probeFetch(page, metadataUrl, { mode: "cors" });
    const downloadRangeResult = await probeFetch(page, downloadUrl, {
      mode: "cors",
      headers: { Range: "bytes=0-15" },
    });

    const result = {
      probe_origin: pageUrl,
      metadata_endpoint: { url: metadataUrl, ...metadataResult },
      download_endpoint_range_request: { url: downloadUrl, ...downloadRangeResult },
    };
    console.log(JSON.stringify(result, null, 2));
  } finally {
    await browser.close();
    server.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
