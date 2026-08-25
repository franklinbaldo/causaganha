from __future__ import annotations

from datetime import date

import httpx
import pytest

from djen_backup import published


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_parquet_404_is_authoritative_absence() -> None:
    client = _client(lambda request: httpx.Response(404, request=request))
    try:
        assert published.read_published_manifest(client=client) is None
    finally:
        client.close()


def test_parquet_5xx_is_unavailable_not_absent() -> None:
    client = _client(lambda request: httpx.Response(503, request=request))
    try:
        with pytest.raises(published.PublishedManifestUnavailable, match="HTTP 503"):
            published.read_published_manifest(client=client)
    finally:
        client.close()


def test_valid_parquet_requires_verifiable_files_metadata(monkeypatch) -> None:
    monkeypatch.setattr(
        published,
        "_read_parquet_rows",
        lambda _path: [
            (
                "TJRO",
                date(2026, 8, 25),
                "uploaded",
                "",
                "",
                "2026-08-25T08:00:00+00:00",
            )
        ],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("sync-manifest.parquet"):
            return httpx.Response(200, content=b"parquet", request=request)
        return httpx.Response(200, json={"unexpected": []}, request=request)

    client = _client(handler)
    try:
        with pytest.raises(
            published.PublishedManifestUnavailable,
            match="metadata is malformed",
        ):
            published.read_published_manifest(client=client)
    finally:
        client.close()


def test_expected_segment_must_be_readable(monkeypatch) -> None:
    monkeypatch.setattr(published, "_read_parquet_rows", lambda _path: [])

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("sync-manifest.parquet"):
            return httpx.Response(200, content=b"parquet", request=request)
        if request.url.path.endswith("/files"):
            return httpx.Response(
                200,
                json={"result": [{"name": "manifest-log/segment.csv"}]},
                request=request,
            )
        return httpx.Response(404, request=request)

    client = _client(handler)
    try:
        with pytest.raises(
            published.PublishedManifestUnavailable,
            match=r"segment.*HTTP 404",
        ):
            published.read_published_manifest(client=client)
    finally:
        client.close()


def test_replays_published_parquet_and_pending_segments(monkeypatch) -> None:
    monkeypatch.setattr(
        published,
        "_read_parquet_rows",
        lambda _path: [
            (
                "TJRO",
                date(2026, 8, 22),
                "uploaded",
                "",
                "",
                "2026-08-23T10:00:00+00:00",
            )
        ],
    )
    segment = (
        "tribunal,date,ia_status,djen_status,djen_raw,updated_at\n"
        "TJRO,2026-08-25,,available,200,2026-08-25T08:00:00+00:00\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("sync-manifest.parquet"):
            return httpx.Response(200, content=b"parquet", request=request)
        if request.url.path.endswith("/files"):
            return httpx.Response(
                200,
                json={"result": [{"name": "manifest-log/segment.csv"}]},
                request=request,
            )
        return httpx.Response(200, text=segment, request=request)

    client = _client(handler)
    try:
        manifest = published.read_published_manifest(client=client)
    finally:
        client.close()

    assert manifest is not None
    counts = manifest.counts()
    assert counts.total == 2
    assert counts.uploaded == 1
    assert counts.available == 1
    assert counts.ultima_atualizacao == "2026-08-25T08:00:00+00:00"
