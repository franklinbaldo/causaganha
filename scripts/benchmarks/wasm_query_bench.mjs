#!/usr/bin/env node
// DuckDB-WASM side of issue #1471's query-cost measurement.
//
// Runs the same date-only (no CNJ) COUNT(*) query as the Python native-engine
// benchmark, in a real headless Chromium page loading the actual browser
// build of `@duckdb/duckdb-wasm` (the same package/worker/httpfs path
// `web/src/lib/duckdbSingleton.ts` ships to production) — not the Node
// "blocking" build, which has no browser Worker and whose httpfs
// implementation does not speak plain HTTP the way the real dashboard's
// in-browser fetch does.
//
// The target page and the `@duckdb/duckdb-wasm` static assets are both
// served by the same local Range-serving HTTP server (see
// `pilot_tjro_2026_query_cost.serve_directory`), so all fetches are
// same-origin and no CORS configuration is needed. Request/byte accounting
// happens entirely in-page via that server's `/__stats__` and `/__reset__`
// endpoints — this subprocess only forwards the final JSON result.
//
// Usage:
//   node scripts/benchmarks/wasm_query_bench.mjs --url http://127.0.0.1:PORT/file.parquet \
//     --page-url http://127.0.0.1:PORT/wasm_query_bench_page.html \
//     --start 2026-06-01 --end 2026-06-01 --warm-iterations 5
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require(
  require.resolve("playwright", { paths: ["/opt/node22/lib/node_modules"] })
);

function parseArgs(argv) {
  const args = { warmIterations: 5 };
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (key === "--url") args.url = argv[++i];
    else if (key === "--page-url") args.pageUrl = argv[++i];
    else if (key === "--start") args.start = argv[++i];
    else if (key === "--end") args.end = argv[++i];
    else if (key === "--warm-iterations") args.warmIterations = Number(argv[++i]);
  }
  if (!args.url || !args.pageUrl || !args.start || !args.end) {
    throw new Error(
      "Usage: --url <parquet-url> --page-url <bench-page-url> --start <date> --end <date> [--warm-iterations N]"
    );
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const query = new URLSearchParams({
    url: args.url,
    start: args.start,
    end: args.end,
    warmIterations: String(args.warmIterations),
  });

  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    page.on("console", (msg) => process.stderr.write(`[page console] ${msg.text()}\n`));
    page.on("pageerror", (err) => process.stderr.write(`[page error] ${err}\n`));

    // DuckDB-WASM's httpfs extension is fetched from extensions.duckdb.org on
    // LOAD. Routing the whole browser through the sandbox's egress proxy
    // breaks fetches to our own plain-HTTP local server (this proxy only
    // accepts HTTPS CONNECT tunnels), so instead this one host is served
    // from a Node-side fetch — which does reach the proxy correctly via
    // NODE_USE_ENV_PROXY — while everything else stays direct.
    await page.route("https://extensions.duckdb.org/**", async (route) => {
      const response = await fetch(route.request().url());
      const body = Buffer.from(await response.arrayBuffer());
      await route.fulfill({ status: response.status, body });
    });

    await page.goto(`${args.pageUrl}?${query.toString()}`);
    await page.waitForFunction(() => window.__BENCH_RESULT__ !== undefined);
    const result = await page.evaluate(() => window.__BENCH_RESULT__);
    if (result && result.error) {
      throw new Error(`in-page benchmark failed: ${result.error}`);
    }
    process.stdout.write(JSON.stringify(result));
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  process.stderr.write(String((err && err.stack) || err) + "\n");
  process.exit(1);
});
