#!/usr/bin/env python3
"""Real-browser CORS regression probe for issue #1482.

`DuckDBExplorer.svelte` runs `read_parquet('https://archive.org/download/
{item}/{file}.parquet')` through DuckDB-WASM's httpfs extension directly in
the browser tab -- a real cross-origin `fetch` from whatever origin the
dashboard is served from. It also does a plain `fetch('https://archive.org/
metadata/{id}/files')` first to check dataset existence. Issue #1482 found
that archive.org's file-*download* endpoint (unlike its `/metadata` and
`/advancedsearch.php` endpoints) sends no `Access-Control-Allow-Origin`
header, so a real browser blocks the download fetch outright.

This was previously checked by `scripts/benchmarks/archive_cors_probe.mjs`
(Node + Playwright), which resolved its `playwright` import through a path
that only exists inside a Claude Code sandbox
(`require.resolve('playwright', { paths: ['/opt/node22/lib/node_modules'] })`)
and was never wired into CI. `playwright` is already a declared Python `dev`
dependency (`pyproject.toml`) but was unused anywhere in this repo -- this
script uses it instead, so a plain `uv sync` + `uv run playwright install
chromium` makes it runnable in real CI, not just this one sandbox image.

Usage:
    uv run python -m scripts.benchmarks.archive_cors_probe \\
        --output docs/planning/evidence/archive-cors-probe-real-browser.json

    # In an environment whose only pre-installed Chromium build doesn't
    # match this project's pinned Playwright version (as in some sandboxes):
    uv run python -m scripts.benchmarks.archive_cors_probe \\
        --chromium-path /opt/pw-browsers/chromium
"""

from __future__ import annotations

import argparse
import http.server
import json
import sys
import threading
from dataclasses import asdict, dataclass
from enum import Enum

from playwright.sync_api import sync_playwright

ITEM_ID = "djen-tjro-2026"
FILENAME = "comunicacoes.parquet"
METADATA_URL = f"https://archive.org/metadata/{ITEM_ID}/files"
DOWNLOAD_URL = f"https://archive.org/download/{ITEM_ID}/{FILENAME}"

_FETCH_PROBE_JS = """
async ({ url, init }) => {
  try {
    const response = await fetch(url, init);
    const body = await response.arrayBuffer();
    return { ok: true, status: response.status, type: response.type, bodyBytes: body.byteLength };
  } catch (error) {
    return { ok: false, errorName: error.name, errorMessage: String(error.message ?? error) };
  }
}
"""


@dataclass(frozen=True)
class FetchOutcome:
    """One in-page `fetch()` call's outcome, as classified by the browser itself."""

    url: str
    ok: bool
    status: int | None = None
    type: str | None = None
    body_bytes: int | None = None
    error_name: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class CorsProbeResult:
    probe_origin: str
    metadata_endpoint: FetchOutcome
    download_endpoint_range_request: FetchOutcome


class Verdict(str, Enum):
    EXPECTED_BLOCKED = "expected_blocked"
    DOWNLOAD_NOW_ALLOWED = "download_now_allowed"
    METADATA_ENDPOINT_BROKEN = "metadata_endpoint_broken"


@dataclass(frozen=True)
class ProbeVerdict:
    verdict: Verdict
    passed: bool
    message: str


def evaluate_cors_probe_result(result: CorsProbeResult) -> ProbeVerdict:
    """Turn a probe result into a pass/fail regression verdict.

    The `/metadata` endpoint is a positive control: real cross-origin CORS
    support that has nothing to do with issue #1482. If it ever fails, the
    probe itself is broken (or archive.org's CORS story is worse than
    documented) -- either way that is the real regression to flag, not the
    already-known download block. If the download endpoint ever starts
    succeeding, that is genuinely new information (archive.org may have
    fixed CORS) and worth a human's attention even though nothing broke.
    """
    metadata = result.metadata_endpoint
    download = result.download_endpoint_range_request

    if not metadata.ok or metadata.type != "cors":
        return ProbeVerdict(
            verdict=Verdict.METADATA_ENDPOINT_BROKEN,
            passed=False,
            message=(
                "archive.org's /metadata endpoint (positive control) failed or lost its "
                "CORS header -- this is a real regression, not issue #1482's known block. "
                f"metadata_endpoint={metadata!r}"
            ),
        )

    if download.ok:
        return ProbeVerdict(
            verdict=Verdict.DOWNLOAD_NOW_ALLOWED,
            passed=False,
            message=(
                "archive.org's /download endpoint now succeeds cross-origin -- issue "
                "#1482's CORS block may have been lifted. DuckDBExplorer.svelte's "
                "cors-blocked classification would need revisiting."
            ),
        )

    return ProbeVerdict(
        verdict=Verdict.EXPECTED_BLOCKED,
        passed=True,
        message="archive.org's /download endpoint is still CORS-blocked cross-origin, as issue #1482 documented.",
    )


def _serve_blank_page() -> tuple[http.server.HTTPServer, str]:
    """Serve a blank page over real HTTP so the browser sends a real Origin header.

    A `file://` document has an opaque/null origin that behaves differently
    under CORS than a real HTTP(S) origin like the production dashboard's.
    """

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler's own naming)
            body = b"<!doctype html><title>cors-probe</title>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    return server, f"http://127.0.0.1:{port}/"


def run_probe(*, chromium_path: str | None = None) -> CorsProbeResult:
    """Drive a real headless Chromium page against live archive.org."""
    server, page_url = _serve_blank_page()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=chromium_path,
                args=["--ignore-certificate-errors"],
            )
            try:
                page = browser.new_page(ignore_https_errors=True)
                page.goto(page_url)

                metadata_raw = page.evaluate(
                    _FETCH_PROBE_JS, {"url": METADATA_URL, "init": {"mode": "cors"}}
                )
                download_raw = page.evaluate(
                    _FETCH_PROBE_JS,
                    {
                        "url": DOWNLOAD_URL,
                        "init": {"mode": "cors", "headers": {"Range": "bytes=0-15"}},
                    },
                )
            finally:
                browser.close()
    finally:
        server.shutdown()

    return CorsProbeResult(
        probe_origin=page_url,
        metadata_endpoint=_outcome_from_js(METADATA_URL, metadata_raw),
        download_endpoint_range_request=_outcome_from_js(DOWNLOAD_URL, download_raw),
    )


def _outcome_from_js(url: str, raw: dict) -> FetchOutcome:
    return FetchOutcome(
        url=url,
        ok=raw["ok"],
        status=raw.get("status"),
        type=raw.get("type"),
        body_bytes=raw.get("bodyBytes"),
        error_name=raw.get("errorName"),
        error_message=raw.get("errorMessage"),
    )


def _result_to_json(result: CorsProbeResult, verdict: ProbeVerdict) -> dict:
    return {
        "probe_origin": result.probe_origin,
        "metadata_endpoint": asdict(result.metadata_endpoint),
        "download_endpoint_range_request": asdict(result.download_endpoint_range_request),
        "verdict": verdict.verdict.value,
        "passed": verdict.passed,
        "message": verdict.message,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=str, default=None, help="Path to write the JSON report")
    parser.add_argument(
        "--chromium-path",
        type=str,
        default=None,
        help="Explicit Chromium executable (only needed when the pre-installed "
        "browser doesn't match Playwright's pinned version, e.g. some sandboxes)",
    )
    args = parser.parse_args()

    result = run_probe(chromium_path=args.chromium_path)
    verdict = evaluate_cors_probe_result(result)
    report = _result_to_json(result, verdict)

    output = json.dumps(report, indent=2, ensure_ascii=False)
    print(output)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)

    if not verdict.passed:
        print(f"CORS PROBE FAILED: {verdict.message}", file=sys.stderr)
    return 0 if verdict.passed else 1


if __name__ == "__main__":
    sys.exit(main())
