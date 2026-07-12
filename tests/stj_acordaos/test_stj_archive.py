"""Tests for stj_acordaos.archive — IA headers, retry classification, no real upload."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import unquote

import httpx
import pytest
import respx

from stj_acordaos.archive import IA_ITEM_ID, MANIFEST_DOWNLOAD_URL, fetch_manifest, upload_parquet


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def parquet_file(tmp_path: Path) -> Path:
    p = tmp_path / "stj-acordaos.parquet"
    p.write_bytes(b"PAR1-fake-bytes")
    return p


def _upload_url(name: str) -> str:
    return f"https://s3.us.archive.org/{IA_ITEM_ID}/{name}"


def test_upload_sends_ia_metadata_headers(parquet_file: Path) -> None:
    with respx.mock() as router:
        route = router.put(_upload_url(parquet_file.name)).respond(200)
        assert upload_parquet(parquet_file, "mykey", "mysecret") is True

    request = route.calls.last.request
    assert request.headers["Authorization"] == "LOW mykey:mysecret"
    assert request.headers["x-archive-auto-make-bucket"] == "1"
    assert request.headers["x-archive-meta-mediatype"] == "data"
    # Non-ASCII metadata must use IA's uri(...) percent-encoding convention —
    # raw UTF-8 in a header would crash httpx with UnicodeEncodeError.
    title = request.headers["x-archive-meta-title"]
    assert title.startswith("uri(")
    assert title.endswith(")")
    assert title.isascii()
    assert unquote(title[4:-1]) == "STJ Acórdãos — Primeira Seção"
    assert request.headers["x-archive-meta-description"].isascii()
    # IA wants x-archive-meta-*, never boto3-style x-amz-meta-* (CLAUDE.md)
    assert not any(h.lower().startswith("x-amz-meta") for h in request.headers)
    assert request.content == b"PAR1-fake-bytes"


def test_upload_403_is_non_retriable_and_fails_once(parquet_file: Path) -> None:
    """403 is a hard auth/WAF failure: report False after ONE attempt, no retry storm."""
    with respx.mock() as router:
        route = router.put(_upload_url(parquet_file.name)).respond(403)
        assert upload_parquet(parquet_file, "k", "s") is False

    assert route.call_count == 1


def test_upload_retries_retriable_status_then_succeeds(parquet_file: Path) -> None:
    with respx.mock() as router:
        route = router.put(_upload_url(parquet_file.name))
        route.side_effect = [httpx.Response(503), httpx.Response(200)]
        assert upload_parquet(parquet_file, "k", "s") is True

    assert route.call_count == 2


def test_upload_exhausts_retries_on_persistent_503(parquet_file: Path) -> None:
    with respx.mock() as router:
        route = router.put(_upload_url(parquet_file.name)).respond(503)
        assert upload_parquet(parquet_file, "k", "s") is False

    # max_retries=5 → initial attempt + 5 retries
    assert route.call_count == 6


def test_upload_network_error_retries_then_fails(parquet_file: Path) -> None:
    """Transport errors (timeout/network) are retried, then reported as failure —
    they never crash the pipeline nor masquerade as success.
    """
    with respx.mock() as router:
        route = router.put(_upload_url(parquet_file.name))
        route.side_effect = httpx.ConnectError("connection refused")
        assert upload_parquet(parquet_file, "k", "s") is False

    assert route.call_count == 6


def test_upload_timeout_then_success(parquet_file: Path) -> None:
    with respx.mock() as router:
        route = router.put(_upload_url(parquet_file.name))
        route.side_effect = [httpx.ConnectTimeout("slow"), httpx.Response(200)]
        assert upload_parquet(parquet_file, "k", "s") is True

    assert route.call_count == 2


# ── fetch_manifest (blank-runner incrementality) ──────────────────────────


def test_fetch_manifest_restores_from_ia(tmp_path: Path) -> None:
    dest = tmp_path / "stj-manifest.csv"
    with respx.mock() as router:
        router.get(MANIFEST_DOWNLOAD_URL).respond(200, content=b"arquivo,tipo\na.zip,zip\n")
        assert fetch_manifest(dest) is True
    assert dest.read_bytes() == b"arquivo,tipo\na.zip,zip\n"


def test_fetch_manifest_missing_on_ia_returns_false_not_raise(tmp_path: Path) -> None:
    """First-ever run: the manifest hasn't been uploaded yet — not an error."""
    dest = tmp_path / "stj-manifest.csv"
    with respx.mock() as router:
        router.get(MANIFEST_DOWNLOAD_URL).respond(404)
        assert fetch_manifest(dest) is False
    assert not dest.exists()


def test_fetch_manifest_server_error_raises_not_treated_as_absent(tmp_path: Path) -> None:
    """A flaky network must not silently look like 'no manifest' (re-download everything)."""
    dest = tmp_path / "stj-manifest.csv"
    with respx.mock() as router:
        router.get(MANIFEST_DOWNLOAD_URL).respond(503)
        with pytest.raises(httpx.HTTPStatusError):
            fetch_manifest(dest)
    assert not dest.exists()
