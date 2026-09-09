"""_download_segment — a Range GET must be honored with 206, not silently
accepted as a full-body 200.

CloudFront/WAF in front of DJEN can, under load-shedding or caching, answer a
ranged GET with a full 200 response instead of a 206 Partial Content. Before
this fix, ``_download_segment`` treated any non-5xx status as success and
returned ``resp.content`` unchecked, so ``download_zip`` would concatenate
oversized/duplicated segment bodies into a silently corrupt ZIP that still
gets uploaded to Internet Archive with no error anywhere in the chain.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from djen_backup.djen import _download_segment


@pytest.mark.asyncio
async def test_download_segment_rejects_response_that_ignores_range_header() -> None:
    with respx.mock(assert_all_called=False) as router:
        # Server ignores the Range header and returns the whole body with a
        # plain 200 OK instead of honoring it with 206 Partial Content.
        router.get("https://djen.example/djen.zip").respond(200, content=b"whole-file-body")
        async with httpx.AsyncClient() as client:
            with pytest.raises(httpx.HTTPError):
                await _download_segment(client, "https://djen.example/djen.zip", start=0, end=99)


@pytest.mark.asyncio
async def test_download_segment_accepts_partial_content() -> None:
    with respx.mock(assert_all_called=False) as router:
        router.get("https://djen.example/djen.zip").respond(
            206,
            content=b"segment-bytes",
            headers={"Content-Range": "bytes 0-99/1000"},
        )
        async with httpx.AsyncClient() as client:
            result = await _download_segment(
                client, "https://djen.example/djen.zip", start=0, end=99
            )
    assert result == b"segment-bytes"
