"""Tests for the DuckDB query-cost helpers used by issue #1471's perf measurement.

Two independently testable pieces:

- `count_row_groups_touched`: a deterministic, network-free proxy for how many
  Parquet row groups a date-only predicate (no CNJ) must scan, given the
  file's actual physical ordering. This is what quantifies the pruning
  regression the issue is worried about: reordering by `numero_processo`
  scatters same-day rows across every row group.
- `serve_directory`: a minimal Range-aware static HTTP server used to get
  *real* bytes/requests/duration numbers out of DuckDB's `httpfs` (both
  native and WASM) instead of relying only on the footer-stats proxy above.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import httpx

from scripts.benchmarks.pilot_tjro_2026_query_cost import (
    count_row_groups_touched,
    serve_directory,
)


def _write_table(tmp_path: Path, name: str, dates: list[str]) -> Path:
    path = tmp_path / name
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE t (numero_processo VARCHAR, data_disponibilizacao DATE, id VARCHAR)")
    con.executemany(
        "INSERT INTO t VALUES ('000', ?::DATE, ?)",
        [(d, f"id-{i:05d}") for i, d in enumerate(dates)],
    )
    # Below DuckDB's ~2048-row vector-size floor ROW_GROUP_SIZE has no effect
    # (see tests/test_validate_pilot_tjro_2026.py) — 2048 reliably splits this
    # fixture into multiple physical row groups.
    con.execute(f"COPY t TO '{path.as_posix()}' (FORMAT PARQUET, ROW_GROUP_SIZE 2048)")
    return path


class TestCountRowGroupsTouched:
    def test_date_sorted_file_prunes_to_few_row_groups(self, tmp_path: Path) -> None:
        # 20 distinct dates, 1000 rows each, written in date order: each row
        # group covers a narrow, mostly non-overlapping date span.
        dates = [f"2026-01-{(i // 1000) + 1:02d}" for i in range(20_000)]
        path = _write_table(tmp_path, "date_sorted.parquet", dates)
        con = duckdb.connect(":memory:")

        total_groups = con.execute(
            "SELECT count(DISTINCT row_group_id) FROM parquet_metadata(?)", [path.as_posix()]
        ).fetchone()[0]
        assert total_groups > 1, "fixture must itself span multiple row groups"

        touched = count_row_groups_touched(con, path, "2026-01-10", "2026-01-10")
        assert 1 <= touched < total_groups

    def test_cnj_scattered_file_touches_every_row_group(self, tmp_path: Path) -> None:
        # Same 20 dates and row count, but interleaved so every physical row
        # group spans (nearly) the full date range — the effect of sorting by
        # numero_processo first (the new candidate ordering).
        dates = [f"2026-01-{(i % 20) + 1:02d}" for i in range(20_000)]
        path = _write_table(tmp_path, "cnj_scattered.parquet", dates)
        con = duckdb.connect(":memory:")

        total_groups = con.execute(
            "SELECT count(DISTINCT row_group_id) FROM parquet_metadata(?)", [path.as_posix()]
        ).fetchone()[0]
        assert total_groups > 1

        touched = count_row_groups_touched(con, path, "2026-01-10", "2026-01-10")
        assert touched == total_groups

    def test_scattered_touches_strictly_more_groups_than_sorted(self, tmp_path: Path) -> None:
        sorted_dates = [f"2026-01-{(i // 1000) + 1:02d}" for i in range(20_000)]
        scattered_dates = [f"2026-01-{(i % 20) + 1:02d}" for i in range(20_000)]
        sorted_path = _write_table(tmp_path, "sorted.parquet", sorted_dates)
        scattered_path = _write_table(tmp_path, "scattered.parquet", scattered_dates)
        con = duckdb.connect(":memory:")

        touched_sorted = count_row_groups_touched(con, sorted_path, "2026-01-10", "2026-01-10")
        touched_scattered = count_row_groups_touched(
            con, scattered_path, "2026-01-10", "2026-01-10"
        )
        assert touched_scattered > touched_sorted


class TestServeDirectory:
    def test_plain_get_returns_full_file_and_records_stats(self, tmp_path: Path) -> None:
        content = b"0123456789" * 100
        (tmp_path / "file.bin").write_bytes(content)

        with serve_directory(tmp_path) as (base_url, stats):
            resp = httpx.get(f"{base_url}/file.bin")
            assert resp.status_code == 200
            assert resp.content == content

            requests, nbytes = stats.snapshot()
            assert requests == 1
            assert nbytes == len(content)

    def test_range_get_returns_partial_content_and_records_bytes(self, tmp_path: Path) -> None:
        content = bytes(range(256)) * 4  # 1024 distinct-ish bytes
        (tmp_path / "file.bin").write_bytes(content)

        with serve_directory(tmp_path) as (base_url, stats):
            resp = httpx.get(f"{base_url}/file.bin", headers={"Range": "bytes=10-19"})
            assert resp.status_code == 206
            assert resp.content == content[10:20]
            assert resp.headers["Content-Range"] == f"bytes 10-19/{len(content)}"

            requests, nbytes = stats.snapshot()
            assert requests == 1
            assert nbytes == 10

    def test_suffix_range_returns_last_n_bytes(self, tmp_path: Path) -> None:
        content = bytes(range(256))
        (tmp_path / "file.bin").write_bytes(content)

        with serve_directory(tmp_path) as (base_url, stats):
            resp = httpx.get(f"{base_url}/file.bin", headers={"Range": "bytes=-10"})
            assert resp.status_code == 206
            assert resp.content == content[-10:]

    def test_query_string_is_ignored_when_resolving_the_file(self, tmp_path: Path) -> None:
        # The bench HTML page is requested as `page.html?url=...&start=...` —
        # the query string must not become part of the resolved file path.
        (tmp_path / "page.html").write_bytes(b"<html></html>")

        with serve_directory(tmp_path) as (base_url, _stats):
            resp = httpx.get(f"{base_url}/page.html?url=http://example.com&start=2026-01-01")
            assert resp.status_code == 200
            assert resp.content == b"<html></html>"

    def test_missing_file_returns_404(self, tmp_path: Path) -> None:
        with serve_directory(tmp_path) as (base_url, _stats):
            resp = httpx.get(f"{base_url}/does-not-exist.bin")
            assert resp.status_code == 404

    def test_reset_clears_counters(self, tmp_path: Path) -> None:
        (tmp_path / "file.bin").write_bytes(b"x" * 50)

        with serve_directory(tmp_path) as (base_url, stats):
            httpx.get(f"{base_url}/file.bin")
            assert stats.snapshot() == (1, 50)

            stats.reset()
            assert stats.snapshot() == (0, 0)

    def test_multiple_requests_accumulate(self, tmp_path: Path) -> None:
        (tmp_path / "file.bin").write_bytes(b"x" * 50)

        with serve_directory(tmp_path) as (base_url, stats):
            httpx.get(f"{base_url}/file.bin")
            httpx.get(f"{base_url}/file.bin", headers={"Range": "bytes=0-9"})

            requests, nbytes = stats.snapshot()
            assert requests == 2
            assert nbytes == 60

    def test_stats_endpoint_reflects_python_side_counters(self, tmp_path: Path) -> None:
        (tmp_path / "file.bin").write_bytes(b"x" * 50)

        with serve_directory(tmp_path) as (base_url, stats):
            httpx.get(f"{base_url}/file.bin")

            resp = httpx.get(f"{base_url}/__stats__")
            assert resp.status_code == 200
            assert resp.json() == {"requests": 1, "bytes": 50}

    def test_reset_endpoint_clears_counters_seen_by_stats_endpoint(self, tmp_path: Path) -> None:
        (tmp_path / "file.bin").write_bytes(b"x" * 50)

        with serve_directory(tmp_path) as (base_url, stats):
            httpx.get(f"{base_url}/file.bin")
            reset_resp = httpx.post(f"{base_url}/__reset__")
            assert reset_resp.status_code == 204

            resp = httpx.get(f"{base_url}/__stats__")
            assert resp.json() == {"requests": 0, "bytes": 0}
            assert stats.snapshot() == (0, 0)
