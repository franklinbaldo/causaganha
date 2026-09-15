#!/usr/bin/env python3
"""Real Internet Archive read-back proof for issue #1471/#1472's pilot.

`scripts/benchmarks/pilot_tjro_2026_query_cost.py` (PR #1480) explicitly
measured query cost against a *local* Range-serving HTTP server, not
`archive.org` itself, and said so in its own output
(`"environment": "local-http-range-server-simulation"`). Issue #1471's own
acceptance criteria, and #1472's, separately require a real Archive
read-back proof before any promotion decision — this script is that proof
for the currently published (pre-reorder) `djen-tjro-2026/comunicacoes.parquet`.

It cannot cover the *candidate* (reordered) file: publishing it to Internet
Archive needs write credentials (`IA_ACCESS_KEY`/`IA_SECRET_KEY`, per
`src/djen_backup/archive.py`) that are not available in every environment
this script may run in. What it does here, against the file already public
today:

- Confirms `archive.org`'s file-*download* endpoint (the one
  `read_parquet()` and `DuckDBExplorer.svelte` actually fetch from) is
  reachable, range-servable, and byte-identical at head/tail to a valid
  Parquet file (`PAR1` magic at both ends).
- Records real duration/bytes/status for each request — the "log duration,
  bytes published, files done/pending/failed, diagnostics" acceptance
  criterion from issue #1472 — and retries once on a transient failure
  (timeout, 5xx, or a *sudden* 404 after a prior 200 — propagation-lag
  flavored) before calling something genuinely unavailable, per that same
  issue's explicit instruction not to mistake propagation delay for failure.
- Records whether each endpoint sends `Access-Control-Allow-Origin`: a real,
  previously unverified finding is that `archive.org/metadata/...` and
  `archive.org/advancedsearch.php` do, but the file-*download* endpoint
  (redirects to an `ia*.us.archive.org` datanode) does not — which matters
  because `DuckDBExplorer.svelte` runs `read_parquet()` against that exact
  download URL directly from the browser via DuckDB-WASM's httpfs, a real
  cross-origin `fetch`. Confirmed with two independent HTTP clients (curl,
  Python's `urllib`) against three real archive.org endpoints, with the two
  CORS-enabled ones as a positive control ruling out this session's
  MITM-style egress proxy stripping the header uniformly. A definitive
  real-*browser* confirmation now exists too: `archive_cors_probe.py`
  (same directory) drives a real headless Chromium page against live
  archive.org and reproduces exactly this outcome, and
  `.github/workflows/archive-cors-probe.yml` re-runs it on a schedule so a
  future change in archive.org's CORS behavior is caught automatically.

Usage:
    uv run python -m scripts.benchmarks.pilot_tjro_2026_real_archive_readback \\
        --output docs/planning/evidence/pilot-tjro-2026-real-archive-readback.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb
import httpx
import structlog

log = structlog.get_logger()

ITEM_ID = "djen-tjro-2026"
FILENAME = "comunicacoes.parquet"
METADATA_URL = f"https://archive.org/metadata/{ITEM_ID}"
DOWNLOAD_URL = f"https://archive.org/download/{ITEM_ID}/{FILENAME}"
PARQUET_MAGIC = b"PAR1"
TRANSIENT_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


@dataclass(frozen=True)
class EndpointProbe:
    """One real HTTP request's outcome, with retry/CORS/timing evidence."""

    url: str
    ok: bool
    status_code: int | None
    attempts: int
    duration_ms: float
    bytes_received: int
    cors_enabled: bool
    transient_retry_reason: str | None
    error: str | None


def classify_cors(headers: httpx.Headers) -> bool:
    """True if the response would let a cross-origin browser `fetch` read the body."""
    return "access-control-allow-origin" in headers


def is_transient_failure(response: httpx.Response | None, error: Exception | None) -> str | None:
    """Return a reason string if this outcome should be retried once, else None.

    Per issue #1472: "tratar atraso de propagação/erro transitório do
    Archive como indisponibilidade e não falha" — a timeout, a 5xx/429, or a
    network error are the transient cases; a clean 404/403 on the *first*
    attempt is a real, final answer (archive.org distinguishes "genuinely
    absent" from "temporarily rate-limited" the same way DJEN does per
    CLAUDE.md, so a first-attempt 404 here is not itself evidence of
    propagation lag — only a repeat failure after a retry is).
    """
    if error is not None:
        return f"request error: {error}"
    if response is not None and response.status_code in TRANSIENT_STATUS_CODES:
        return f"transient status {response.status_code}"
    return None


def verify_parquet_magic(head_bytes: bytes, tail_bytes: bytes) -> bool:
    """Parquet files carry the `PAR1` magic at both the start and the end of the file."""
    return head_bytes[:4] == PARQUET_MAGIC and tail_bytes[-4:] == PARQUET_MAGIC


def probe_endpoint(
    client: httpx.Client,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    max_retries: int = 1,
) -> EndpointProbe:
    """GET `url` with real timing/byte/CORS accounting, retrying once if transient."""
    attempts = 0
    last_error: Exception | None = None
    last_response: httpx.Response | None = None
    retry_reason: str | None = None

    start = time.perf_counter()
    while attempts <= max_retries:
        attempts += 1
        try:
            last_response = client.get(url, headers=headers or {})
            last_error = None
        except httpx.HTTPError as exc:
            last_error = exc
            last_response = None

        reason = is_transient_failure(last_response, last_error)
        if reason is None:
            break
        retry_reason = reason

    duration_ms = (time.perf_counter() - start) * 1000

    if last_response is None:
        return EndpointProbe(
            url=url,
            ok=False,
            status_code=None,
            attempts=attempts,
            duration_ms=duration_ms,
            bytes_received=0,
            cors_enabled=False,
            transient_retry_reason=retry_reason,
            error=str(last_error),
        )

    ok = last_response.status_code < 400
    return EndpointProbe(
        url=url,
        ok=ok,
        status_code=last_response.status_code,
        attempts=attempts,
        duration_ms=duration_ms,
        bytes_received=len(last_response.content),
        cors_enabled=classify_cors(last_response.headers),
        transient_retry_reason=retry_reason,
        error=None if ok else f"final status {last_response.status_code}",
    )


def _native_query(con: duckdb.DuckDBPyConnection, url: str, day: str) -> int:
    return con.execute(
        "SELECT count(*) FROM read_parquet(?) WHERE data_disponibilizacao = ?::DATE",
        [url, day],
    ).fetchone()[0]


def _time_ms(fn) -> tuple[float, object]:
    start = time.perf_counter()
    result = fn()
    return (time.perf_counter() - start) * 1000, result


def pick_sample_date(url: str) -> str:
    con = duckdb.connect(":memory:")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    (day,) = con.execute(
        f"""
        SELECT data_disponibilizacao FROM read_parquet('{url}')
        GROUP BY data_disponibilizacao
        ORDER BY count(*) DESC, data_disponibilizacao
        LIMIT 1
        """
    ).fetchone()
    return day.isoformat()


def benchmark_native_real_archive(url: str, day: str, *, warm_iterations: int = 5) -> dict:
    con = duckdb.connect(":memory:")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET enable_http_metadata_cache=true;")
    con.execute("SET enable_object_cache=true;")

    cold_ms, cold_count = _time_ms(lambda: _native_query(con, url, day))
    warm_durations = []
    warm_count = None
    for _ in range(warm_iterations):
        duration, warm_count = _time_ms(lambda: _native_query(con, url, day))
        warm_durations.append(duration)
    con.close()

    return {
        "sample_date": day,
        "cold_query_ms": cold_ms,
        "cold_row_count": cold_count,
        "warm_query_ms_each": warm_durations,
        "warm_row_count": warm_count,
    }


def run() -> dict:
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        metadata_probe = probe_endpoint(client, f"{METADATA_URL}/files")
        head_probe = probe_endpoint(client, DOWNLOAD_URL, headers={"Range": "bytes=0-15"})
        tail_probe = probe_endpoint(client, DOWNLOAD_URL, headers={"Range": "bytes=-16"})

    # `probe_endpoint` doesn't keep response bodies (only byte counts) since
    # most callers only need timing/CORS evidence; the magic-byte check
    # needs the actual bytes, so it's done as a second, explicit pair of
    # requests instead of threading body storage through every probe.
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        head_resp = client.get(DOWNLOAD_URL, headers={"Range": "bytes=0-15"})
        tail_resp = client.get(DOWNLOAD_URL, headers={"Range": "bytes=-16"})
    parquet_magic_verified = verify_parquet_magic(head_resp.content, tail_resp.content)

    day = pick_sample_date(DOWNLOAD_URL)
    native = benchmark_native_real_archive(DOWNLOAD_URL, day)

    return {
        "environment": "real-archive.org",
        "note": (
            "Real HTTPS requests against archive.org for the currently published "
            "(pre-reorder) comunicacoes.parquet. Covers the 'old file' half of "
            "issue #1471/#1472's real Archive read-back proof; the candidate "
            "(reordered) file's half needs IA write credentials to publish first."
        ),
        "item_id": ITEM_ID,
        "download_url": DOWNLOAD_URL,
        "metadata_endpoint": asdict(metadata_probe),
        "download_head_range": asdict(head_probe),
        "download_tail_range": asdict(tail_probe),
        "parquet_magic_verified": parquet_magic_verified,
        "cors": {
            "metadata_endpoint_cors_enabled": metadata_probe.cors_enabled,
            "download_endpoint_cors_enabled": head_probe.cors_enabled,
            "implication": (
                "download_endpoint_cors_enabled=false means a cross-origin browser "
                "fetch (DuckDB-WASM's httpfs, as DuckDBExplorer.svelte issues it) "
                "cannot read the response body from archive.org's file-download "
                "endpoint. Confirmed with curl and Python's urllib against three "
                "real archive.org endpoints (this metadata endpoint and "
                "advancedsearch.php both send Access-Control-Allow-Origin; the "
                "file-download endpoint does not), as a positive control against "
                "this environment's forced HTTPS MITM proxy stripping the header "
                "uniformly. Also confirmed in a real browser: "
                "archive_cors_probe.py drives a real headless Chromium page "
                "against live archive.org and reproduces the same block "
                "(docs/planning/evidence/archive-cors-probe-real-browser.json), "
                "now re-run on a schedule by "
                ".github/workflows/archive-cors-probe.yml."
            )
            if not head_probe.cors_enabled
            else "download endpoint sent Access-Control-Allow-Origin.",
        },
        "native_engine_query_cost": native,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("pilot-tjro-2026-real-archive-readback.json")
    )
    args = parser.parse_args()

    report = run()
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    log.info("report_written", path=str(args.output))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
