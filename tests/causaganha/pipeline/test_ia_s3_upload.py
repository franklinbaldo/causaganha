"""Tests for streamed IA S3 uploads in causaganha.pipeline.ia_s3.

No real network. A small custom httpx transport iterates ``request.stream``
itself: respx would pre-read the body and hide the streaming behaviour under
test. The chunk size is shrunk via monkeypatch so a small file exercises many
chunks.
"""

from __future__ import annotations

import math
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import httpx
import pytest
from tenacity import wait_none

from causaganha.pipeline import ia_s3


if TYPE_CHECKING:
    from pathlib import Path


URL = f"{ia_s3._IA_S3_URL}/djen-trf3-2024/textos.parquet"
PAYLOAD = bytes(range(256)) * 200  # 51_200 bytes, non-trivial content
CHUNK = 4096

Handler = Callable[[httpx.Request], Awaitable[httpx.Response]]


class _Transport(httpx.AsyncBaseTransport):
    """Hands each request, with its unread streaming body, to ``handler``."""

    def __init__(self, handler: Handler) -> None:
        self._handler = handler

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return await self._handler(request)


def _client(handler: Handler) -> httpx.AsyncClient:
    # Mirrors ia_s3.create_upload_client (auth header + redirect following).
    return httpx.AsyncClient(
        transport=_Transport(handler),
        headers={"Authorization": "LOW a:b"},
        follow_redirects=True,
    )


async def _drain(request: httpx.Request) -> list[bytes]:
    return [chunk async for chunk in request.stream]


@pytest.fixture(autouse=True)
def _fast_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop tenacity's real backoff so retry tests run instantly."""
    monkeypatch.setattr(ia_s3._perform_upload.retry, "wait", wait_none())


@pytest.fixture(autouse=True)
def _small_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ia_s3, "_UPLOAD_CHUNK_BYTES", CHUNK)


@pytest.fixture
def payload_file(tmp_path: Path) -> Path:
    path = tmp_path / "textos.parquet"
    path.write_bytes(PAYLOAD)
    return path


async def test_body_is_streamed_in_chunks_not_one_bytes_object(payload_file: Path) -> None:
    seen: list[list[bytes]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(await _drain(request))
        return httpx.Response(200)

    async with _client(handler) as client:
        await ia_s3._perform_upload(client, URL, payload_file, {})

    assert len(seen) == 1
    chunks = seen[0]
    assert len(chunks) == math.ceil(len(PAYLOAD) / CHUNK)  # 13 chunks
    assert all(len(c) <= CHUNK for c in chunks)
    assert b"".join(chunks) == PAYLOAD


async def test_content_length_matches_file_size_and_body_is_not_chunked(
    payload_file: Path,
) -> None:
    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["content_length"] = request.headers["Content-Length"]
        captured["transfer_encoding"] = request.headers.get("Transfer-Encoding", "")
        captured["content_md5"] = request.headers.get("Content-MD5", "")
        await _drain(request)
        return httpx.Response(200)

    async with _client(handler) as client:
        await ia_s3._perform_upload(client, URL, payload_file, {"Content-MD5": "abc"})

    assert captured["content_length"] == str(len(PAYLOAD))
    assert captured["transfer_encoding"] == ""
    assert captured["content_md5"] == "abc"


async def test_retry_after_mid_transfer_oserror_resends_full_body(payload_file: Path) -> None:
    bodies: list[bytes] = []
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            # Consume part of the body, then fail the way a reset socket does.
            await anext(aiter(request.stream))
            raise ConnectionResetError(104, "Connection reset by peer")
        bodies.append(b"".join(await _drain(request)))
        return httpx.Response(200)

    async with _client(handler) as client:
        await ia_s3._perform_upload(client, URL, payload_file, {})

    assert attempts == 2
    assert bodies == [PAYLOAD]


async def test_upload_to_ia_recovers_from_errno0_oserror(payload_file: Path) -> None:
    """The production failure ('[Errno 0] Error') must retry, not give up."""
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError(0, "Error")
        await _drain(request)
        return httpx.Response(200)

    async with _client(handler) as client:
        ok = await ia_s3.upload_to_ia(client, "djen-trf3-2024", payload_file, "2024-01-01")

    assert ok is True
    assert attempts == 2


async def test_redirect_replays_full_body(payload_file: Path) -> None:
    """A 307 must re-send the body; a one-shot generator body would raise StreamConsumed."""
    bodies: list[bytes] = []
    redirected = False

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal redirected
        if not redirected:
            redirected = True
            await _drain(request)
            return httpx.Response(307, headers={"Location": f"{URL}?redirected=1"})
        bodies.append(b"".join(await _drain(request)))
        return httpx.Response(200)

    async with _client(handler) as client:
        await ia_s3._perform_upload(client, URL, payload_file, {})

    assert bodies == [PAYLOAD]


async def test_persistent_oserror_gives_up_after_five_attempts(payload_file: Path) -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise ConnectionResetError(104, "reset")

    async with _client(handler) as client:
        ok = await ia_s3.upload_to_ia(client, "djen-trf3-2024", payload_file, "2024-01-01")

    assert ok is False
    assert attempts == 5


def test_is_retryable_upload_error_classification() -> None:
    req = httpx.Request("PUT", URL)
    assert ia_s3._is_retryable_upload_error(httpx.ConnectError("boom", request=req))
    assert ia_s3._is_retryable_upload_error(ConnectionResetError(104, "reset"))
    assert ia_s3._is_retryable_upload_error(OSError(0, "Error"))
    assert not ia_s3._is_retryable_upload_error(FileNotFoundError(2, "missing"))
    assert not ia_s3._is_retryable_upload_error(PermissionError(13, "denied"))
    assert not ia_s3._is_retryable_upload_error(ValueError("nope"))
    resp_503 = httpx.Response(503, request=req)
    assert ia_s3._is_retryable_upload_error(
        httpx.HTTPStatusError("x", request=req, response=resp_503)
    )
    resp_403 = httpx.Response(403, request=req)
    assert not ia_s3._is_retryable_upload_error(
        httpx.HTTPStatusError("x", request=req, response=resp_403)
    )
