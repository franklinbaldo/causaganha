#!/usr/bin/env python3
"""DuckDB native + WASM query-cost measurement for issue #1471's TJRO 2026 pilot.

Quantifies the still-open acceptance criteria: "Medir consultas por data sem
CNJ para quantificar o custo da nova ordenação" and "Usar DuckDB nativo e
WASM; separar inicialização do motor, consulta fria e cache quente. Registrar
bytes, requisições, duração, amostra e ambiente."

The candidate file (built by PR #1478's unified writer, `ORDER BY
numero_processo, data_disponibilizacao, id`) trades CNJ point-lookup pruning
for date-only pruning: a date-only predicate can no longer rely on row-group
min/max stats, because rows for any given day are now scattered across every
row group instead of clustered together as they are in the currently
published file.

Both engines query the *same* local Range-serving HTTP server (not the real
archive.org endpoint) so bytes/requests/duration are directly comparable
between native and WASM and isolated from network/CDN variance. This is a
controlled local simulation, not the real-Archive read-back proof required
separately by the issue's publish/read-back criterion — that needs an actual
Internet Archive upload and is explicitly left to a follow-up round (see
handoffs/handoff-issue-1471-perf-and-readback).

Usage:
    uv run python -m scripts.benchmarks.pilot_tjro_2026_query_cost \\
        --output docs/planning/evidence/pilot-tjro-2026-query-cost.json
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator

import duckdb

from scripts.validate_pilot_tjro_2026 import build_candidate, download_old_parquet


ROOT = Path(__file__).resolve().parent.parent.parent
WASM_BENCH_SCRIPT = ROOT / "scripts" / "benchmarks" / "wasm_query_bench.mjs"
WARM_ITERATIONS = 5


def count_row_groups_touched(
    con: duckdb.DuckDBPyConnection, path: Path, start_date: str, end_date: str
) -> int:
    """Row groups whose `data_disponibilizacao` stats overlap `[start_date, end_date]`.

    A network-free, deterministic proxy for how many HTTP range reads a
    date-only query would need against this file's physical layout: DuckDB's
    Parquet reader skips a row group only when its footer min/max cannot
    possibly satisfy the predicate.
    """
    return con.execute(
        """
        SELECT count(*) FROM parquet_metadata(?)
        WHERE path_in_schema = 'data_disponibilizacao'
          AND stats_min_value IS NOT NULL
          AND stats_min_value <= ?
          AND stats_max_value >= ?
        """,
        [path.as_posix(), end_date, start_date],
    ).fetchone()[0]


class _RequestStats:
    """Thread-safe request/byte counters for `serve_directory`."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests = 0
        self._bytes = 0

    def record(self, nbytes: int) -> None:
        with self._lock:
            self._requests += 1
            self._bytes += nbytes

    def snapshot(self) -> tuple[int, int]:
        with self._lock:
            return self._requests, self._bytes

    def reset(self) -> None:
        with self._lock:
            self._requests = 0
            self._bytes = 0


_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$")


def _parse_range(header: str, file_size: int) -> tuple[int, int] | None:
    match = _RANGE_RE.match(header.strip())
    if match is None:
        return None
    start_s, end_s = match.groups()
    if start_s == "" and end_s == "":
        return None
    if start_s == "":
        length = int(end_s)
        start, end = max(file_size - length, 0), file_size - 1
    else:
        start = int(start_s)
        end = int(end_s) if end_s else file_size - 1
    if file_size == 0 or start >= file_size or start > end:
        return None
    return start, min(end, file_size - 1)


_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".mjs": "text/javascript",
    ".js": "text/javascript",
    ".wasm": "application/wasm",
    ".parquet": "application/octet-stream",
}


class _RangeRequestHandler(BaseHTTPRequestHandler):
    directory: Path
    stats: _RequestStats

    def _resolve(self) -> Path | None:
        rel = urllib.parse.urlsplit(self.path).path.lstrip("/")
        candidate = (self.directory / rel).resolve()
        if (
            self.directory.resolve() not in candidate.parents
            and candidate != self.directory.resolve()
        ):
            return None
        return candidate if candidate.is_file() else None

    def do_GET(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler's naming contract
        if self.path == "/__stats__":
            requests, nbytes = self.stats.snapshot()
            body = json.dumps({"requests": requests, "bytes": nbytes}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return
        self._serve(with_body=True)

    def do_HEAD(self) -> None:  # noqa: N802
        self._serve(with_body=False)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/__reset__":
            self.stats.reset()
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return
        self.send_error(404)

    def do_OPTIONS(self) -> None:  # noqa: N802 — browser CORS preflight for POST /__reset__
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST")
        self.send_header("Access-Control-Allow-Headers", "Range")
        self.end_headers()

    def _serve(self, *, with_body: bool) -> None:
        file_path = self._resolve()
        if file_path is None:
            self.send_error(404)
            return

        file_size = file_path.stat().st_size
        range_header = self.headers.get("Range")
        byte_range = _parse_range(range_header, file_size) if range_header else None

        if range_header and byte_range is None:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{file_size}")
            self.end_headers()
            return

        if byte_range is not None:
            start, end = byte_range
            length = end - start + 1
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        else:
            start, length = 0, file_size
            self.send_response(200)

        content_type = _CONTENT_TYPES.get(file_path.suffix, "application/octet-stream")
        self.send_header("Content-Type", content_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        self.end_headers()

        # Recorded before the body is flushed to the client: a caller that
        # blocks until the response completes and then immediately snapshots
        # stats must never race a handler thread that hasn't updated the
        # counters yet.
        self.stats.record(length)
        if with_body:
            with file_path.open("rb") as fh:
                fh.seek(start)
                self.wfile.write(fh.read(length))

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 — stdlib signature
        pass


@contextlib.contextmanager
def serve_directory(directory: Path) -> Iterator[tuple[str, _RequestStats]]:
    """Serve `directory` over HTTP with Range support; yields `(base_url, stats)`."""
    stats = _RequestStats()

    class Handler(_RangeRequestHandler):
        pass

    Handler.directory = directory
    Handler.stats = stats

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", stats
    finally:
        httpd.shutdown()
        thread.join(timeout=5)


@dataclass(frozen=True)
class PhaseMeasurement:
    engine: str
    file_label: str
    phase: str
    duration_ms: float
    requests: int
    bytes: int
    row_count: int | None


def _time_ms(fn) -> tuple[float, object]:
    start = time.perf_counter()
    result = fn()
    return (time.perf_counter() - start) * 1000, result


def _native_query(con: duckdb.DuckDBPyConnection, url: str, start_date: str, end_date: str) -> int:
    return con.execute(
        f"""
        SELECT count(*) FROM read_parquet('{url}')
        WHERE data_disponibilizacao BETWEEN ?::DATE AND ?::DATE
        """,
        [start_date, end_date],
    ).fetchone()[0]


def benchmark_native(
    base_url: str,
    file_label: str,
    filename: str,
    start_date: str,
    end_date: str,
    stats: _RequestStats,
) -> list[PhaseMeasurement]:
    url = f"{base_url}/{filename}"
    measurements: list[PhaseMeasurement] = []

    stats.reset()
    init_ms, con = _time_ms(lambda: duckdb.connect(":memory:"))
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET enable_http_metadata_cache=true;")
    con.execute("SET enable_object_cache=true;")
    req, nbytes = stats.snapshot()
    measurements.append(
        PhaseMeasurement("duckdb-native", file_label, "engine_init", init_ms, req, nbytes, None)
    )

    stats.reset()
    cold_ms, cold_count = _time_ms(lambda: _native_query(con, url, start_date, end_date))
    req, nbytes = stats.snapshot()
    measurements.append(
        PhaseMeasurement(
            "duckdb-native", file_label, "cold_query", cold_ms, req, nbytes, cold_count
        )
    )

    stats.reset()
    warm_durations = []
    warm_count = None
    for _ in range(WARM_ITERATIONS):
        duration, warm_count = _time_ms(lambda: _native_query(con, url, start_date, end_date))
        warm_durations.append(duration)
    req, nbytes = stats.snapshot()
    measurements.append(
        PhaseMeasurement(
            "duckdb-native",
            file_label,
            "warm_cache",
            statistics.median(warm_durations),
            req,
            nbytes,
            warm_count,
        )
    )

    con.close()
    return measurements


def benchmark_wasm(
    base_url: str, file_label: str, filename: str, start_date: str, end_date: str
) -> list[PhaseMeasurement]:
    """Run the WASM-side benchmark in a real headless Chromium page.

    Request/byte accounting happens in-page against the same server's
    `/__stats__`/`/__reset__` endpoints (see `wasm_query_bench_page.html`),
    not via the Python-side `_RequestStats` object directly — the browser
    process and this Python process don't share memory, but they do share
    the HTTP server, so routing accounting through it gives each phase (not
    just the whole run) its own request/byte count.
    """
    url = f"{base_url}/{filename}"
    page_url = f"{base_url}/wasm_query_bench_page.html"
    result = subprocess.run(
        [
            "node",
            str(WASM_BENCH_SCRIPT),
            "--url",
            url,
            "--page-url",
            page_url,
            "--start",
            start_date,
            "--end",
            end_date,
            "--warm-iterations",
            str(WARM_ITERATIONS),
        ],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "NODE_USE_ENV_PROXY": "1"},
    )
    payload = json.loads(result.stdout)

    return [
        PhaseMeasurement(
            "duckdb-wasm",
            file_label,
            "engine_init",
            payload["engine_init_ms"],
            payload["engine_init_requests"],
            payload["engine_init_bytes"],
            None,
        ),
        PhaseMeasurement(
            "duckdb-wasm",
            file_label,
            "cold_query",
            payload["cold_query_ms"],
            payload["cold_requests"],
            payload["cold_bytes"],
            payload["cold_row_count"],
        ),
        PhaseMeasurement(
            "duckdb-wasm",
            file_label,
            "warm_cache",
            payload["warm_query_ms_median"],
            payload["warm_requests"],
            payload["warm_bytes"],
            payload["warm_row_count"],
        ),
    ]


def pick_sample_date(old_path: Path) -> tuple[str, str, int]:
    """Pick the busiest single day in the file as the query sample."""
    con = duckdb.connect(":memory:")
    day, row_count = con.execute(
        f"""
        SELECT data_disponibilizacao, count(*) AS n
        FROM read_parquet('{old_path.as_posix()}')
        GROUP BY data_disponibilizacao
        ORDER BY n DESC, data_disponibilizacao
        LIMIT 1
        """
    ).fetchone()
    day_str = day.isoformat()
    return day_str, day_str, row_count


def _stage_wasm_assets(work_dir: Path) -> None:
    """Copy the duckdb-wasm browser bundle and the bench page into `work_dir`.

    Both need to be served by the same local server as the target Parquet
    files so every fetch the bench page makes (module, worker, wasm binary,
    stats endpoints, parquet ranges) is same-origin.
    """
    duckdb_dist = ROOT / "web" / "node_modules" / "@duckdb" / "duckdb-wasm" / "dist"
    dest = work_dir / "_duckdb"
    dest.mkdir(exist_ok=True)
    for name in (
        "duckdb-browser.mjs",
        "duckdb-browser-mvp.worker.js",
        "duckdb-browser-eh.worker.js",
        "duckdb-mvp.wasm",
        "duckdb-eh.wasm",
    ):
        (dest / name).write_bytes((duckdb_dist / name).read_bytes())
    # duckdb-browser.mjs has one bare specifier (`import ... from "apache-arrow"`)
    # that only a bundler (Vite, in production) resolves at build time; the
    # bench page supplies an import map instead so the raw ESM bundle loads
    # unmodified in a plain browser page. Arrow.dom.mjs is a barrel file with
    # its own tree of relative imports, so the whole package is copied, not
    # just its entry point.
    apache_arrow_src = ROOT / "web" / "node_modules" / "apache-arrow"
    apache_arrow_dest = dest / "apache-arrow"
    if not apache_arrow_dest.exists():
        shutil.copytree(apache_arrow_src, apache_arrow_dest)
    # apache-arrow's compiled output imports these two helpers bare too.
    for pkg in ("tslib", "flatbuffers"):
        pkg_dest = dest / pkg
        if not pkg_dest.exists():
            shutil.copytree(ROOT / "web" / "node_modules" / pkg, pkg_dest)
    (work_dir / "wasm_query_bench_page.html").write_bytes(
        (ROOT / "scripts" / "benchmarks" / "wasm_query_bench_page.html").read_bytes()
    )


def run(work_dir: Path) -> dict:
    old_path = work_dir / "old-comunicacoes.parquet"
    old_sha256 = download_old_parquet(old_path)
    candidate_path = build_candidate(old_path, work_dir)
    candidate_path = candidate_path.rename(work_dir / "candidate-comunicacoes.parquet")
    _stage_wasm_assets(work_dir)

    start_date, end_date, sample_row_count = pick_sample_date(old_path)

    measurements: list[PhaseMeasurement] = []
    with serve_directory(work_dir) as (base_url, stats):
        for file_label, filename in (("old", old_path.name), ("candidate", candidate_path.name)):
            measurements += benchmark_native(
                base_url, file_label, filename, start_date, end_date, stats
            )
            measurements += benchmark_wasm(base_url, file_label, filename, start_date, end_date)

    con = duckdb.connect(":memory:")
    row_groups_touched = {
        file_label: count_row_groups_touched(con, path, start_date, end_date)
        for file_label, path in (("old", old_path), ("candidate", candidate_path))
    }

    return {
        "environment": "local-http-range-server-simulation",
        "note": (
            "Both engines query the same local Range-serving HTTP server, not the "
            "real archive.org endpoint. This isolates the effect of physical row "
            "ordering from network/CDN variance; it is NOT the real-Archive "
            "read-back proof the issue's publish criterion separately requires."
        ),
        "old_url": "https://archive.org/download/djen-tjro-2026/comunicacoes.parquet",
        "old_sha256": old_sha256,
        "sample": {
            "kind": "busiest_single_day",
            "date": start_date,
            "row_count": sample_row_count,
        },
        "row_groups_touched": row_groups_touched,
        "measurements": [asdict(m) for m in measurements],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("pilot-tjro-2026-query-cost.json"))
    parser.add_argument("--work-dir", type=Path, default=None)
    args = parser.parse_args()

    work_dir = args.work_dir or Path(tempfile.mkdtemp(prefix="pilot-tjro-2026-cost-"))
    work_dir.mkdir(parents=True, exist_ok=True)

    report = run(work_dir)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
