"""Tests for tjro_juris.archive — IA headers, item naming, failure discipline.

No real network: respx intercepts the PUT to s3.us.archive.org.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import unquote

import httpx
import pytest
import respx

from tjro_juris import archive


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def parquet_file(tmp_path: Path) -> Path:
    p = tmp_path / "2024-01-ACORDAO.parquet"
    p.write_bytes(b"PAR1-tjro-bytes")
    return p


@pytest.fixture
def _fake_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(archive.ia_s3, "get_ia_s3_auth", lambda: "LOW testkey:testsecret")


@pytest.mark.usefixtures("_fake_auth")
async def test_upload_file_sends_ia_metadata_headers(parquet_file: Path) -> None:
    url = "https://s3.us.archive.org/tjro-juris-2024/2024-01-ACORDAO.parquet"
    with respx.mock() as router:
        route = router.put(url).respond(200)
        await archive.upload_file(parquet_file, 2024, "2024-01-ACORDAO.parquet")

    request = route.calls.last.request
    assert request.headers["Authorization"] == "LOW testkey:testsecret"
    assert request.headers["x-archive-auto-make-bucket"] == "1"
    assert request.headers["x-archive-meta-mediatype"] == "data"
    assert "TJRO" in request.headers["x-archive-meta-subject"]
    # Non-ASCII metadata must use IA's uri(...) percent-encoding convention —
    # raw UTF-8 in a header would crash httpx with UnicodeEncodeError.
    description = request.headers["x-archive-meta-description"]
    assert description.startswith("uri(")
    assert description.isascii()
    assert unquote(description[4:-1]).startswith("Jurisprudência do Tribunal")
    # IA wants x-archive-meta-*, never boto3-style x-amz-meta-* (CLAUDE.md)
    assert not any(h.lower().startswith("x-amz-meta") for h in request.headers)
    assert request.content == b"PAR1-tjro-bytes"


@pytest.mark.usefixtures("_fake_auth")
async def test_upload_file_uses_yearly_item_naming(parquet_file: Path) -> None:
    """Items are tjro-juris-{year} buckets, mirroring djen-{tribunal}-{year}."""
    with respx.mock() as router:
        route = router.put(url__startswith="https://s3.us.archive.org/").respond(200)
        await archive.upload_file(parquet_file, 2019, "2019-05-VOTO.parquet")

    assert (
        str(route.calls.last.request.url)
        == "https://s3.us.archive.org/tjro-juris-2019/2019-05-VOTO.parquet"
    )


@pytest.mark.usefixtures("_fake_auth")
async def test_upload_file_raises_on_http_error_status(parquet_file: Path) -> None:
    """A 403/5xx must raise so the caller keeps the entry pending — never 'uploaded'."""
    with respx.mock() as router:
        router.put(url__startswith="https://s3.us.archive.org/").respond(403)
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await archive.upload_file(parquet_file, 2024, "x.parquet")
    assert exc_info.value.response.status_code == 403


@pytest.mark.usefixtures("_fake_auth")
async def test_upload_file_timeout_propagates(parquet_file: Path) -> None:
    with respx.mock() as router:
        router.put(url__startswith="https://s3.us.archive.org/").mock(
            side_effect=httpx.ConnectTimeout("timed out")
        )
        with pytest.raises(httpx.ConnectTimeout):
            await archive.upload_file(parquet_file, 2024, "x.parquet")


async def test_upload_file_without_credentials_raises_runtime_error(
    parquet_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(archive.ia_s3, "get_ia_s3_auth", lambda: None)
    with pytest.raises(RuntimeError, match="credentials"):
        await archive.upload_file(parquet_file, 2024, "x.parquet")
