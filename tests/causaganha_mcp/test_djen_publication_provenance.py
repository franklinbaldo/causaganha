"""Publication-clock contracts for the composed DJEN authority."""

from __future__ import annotations

from datetime import date

import httpx

import causaganha_mcp.tools.status as status_module
from djen_backup import published
from djen_backup.manifest import IA_PARQUET_FILENAME, SyncManifest


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _empty_segment() -> str:
    return "tribunal,date,ia_status,djen_status,djen_raw,updated_at\n"


def test_observation_uses_latest_mtime_from_exact_participants(monkeypatch) -> None:
    monkeypatch.setattr(published, "_read_parquet_rows", lambda _path: [])
    segment_name = "manifest-log/run.csv"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(IA_PARQUET_FILENAME):
            return httpx.Response(200, content=b"parquet", request=request)
        if request.url.path.endswith("/files"):
            return httpx.Response(
                200,
                json={
                    "result": [
                        {"name": IA_PARQUET_FILENAME, "mtime": "1787803200"},
                        {"name": segment_name, "mtime": "1787806800"},
                        {"name": "manifest-log/compacted/old.csv", "mtime": "1787810400"},
                    ]
                },
                request=request,
            )
        if request.url.path.endswith(segment_name):
            return httpx.Response(200, text=_empty_segment(), request=request)
        return httpx.Response(404, request=request)

    client = _client(handler)
    try:
        observation = published.read_published_manifest_observation(client=client)
    finally:
        client.close()

    assert observation is not None
    assert [component.name for component in observation.components] == [
        IA_PARQUET_FILENAME,
        segment_name,
    ]
    assert observation.missing_publication_components == ()
    assert observation.latest_publication == "2026-08-27T05:00:00+00:00"


def test_missing_component_mtime_keeps_content_present_but_clock_unknown(monkeypatch) -> None:
    monkeypatch.setattr(published, "_read_parquet_rows", lambda _path: [])
    segment_name = "manifest-log/run.csv"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(IA_PARQUET_FILENAME):
            return httpx.Response(200, content=b"parquet", request=request)
        if request.url.path.endswith("/files"):
            return httpx.Response(
                200,
                json={
                    "result": [
                        {"name": IA_PARQUET_FILENAME, "mtime": "1787803200"},
                        {"name": segment_name, "mtime": "not-a-time"},
                    ]
                },
                request=request,
            )
        if request.url.path.endswith(segment_name):
            return httpx.Response(200, text=_empty_segment(), request=request)
        return httpx.Response(404, request=request)

    client = _client(handler)
    try:
        observation = published.read_published_manifest_observation(client=client)
    finally:
        client.close()

    assert observation is not None
    assert observation.latest_publication is None
    assert observation.missing_publication_components == (segment_name,)


def test_djen_status_exposes_composed_publication_clock(monkeypatch) -> None:
    manifest = SyncManifest()
    manifest.apply_event(
        "TJRO",
        date(2026, 8, 26),
        ia_status="uploaded",
        updated_at="2026-08-26T12:00:00+00:00",
    )
    observation = published.PublishedManifestObservation(
        manifest=manifest,
        components=(
            published.PublishedComponent(
                name=IA_PARQUET_FILENAME,
                modified_at="2026-08-27T04:00:00+00:00",
            ),
            published.PublishedComponent(
                name="manifest-log/run.csv",
                modified_at="2026-08-27T05:00:00+00:00",
            ),
        ),
    )
    monkeypatch.setattr(
        status_module.djen_published,
        "read_published_manifest_observation",
        lambda: observation,
    )

    result = status_module._djen_status()

    assert result.observacao == "present"
    assert result.publicacao_observacao == "present"
    assert result.ultima_publicacao == "2026-08-27T05:00:00+00:00"
    assert result.publicacao_aviso is None


def test_djen_status_preserves_unknown_when_one_participant_has_no_clock(monkeypatch) -> None:
    manifest = SyncManifest()
    observation = published.PublishedManifestObservation(
        manifest=manifest,
        components=(published.PublishedComponent(name=IA_PARQUET_FILENAME, modified_at=None),),
    )
    monkeypatch.setattr(
        status_module.djen_published,
        "read_published_manifest_observation",
        lambda: observation,
    )

    result = status_module._djen_status()

    assert result.observacao == "present"
    assert result.publicacao_observacao == "unknown"
    assert result.ultima_publicacao is None
    assert IA_PARQUET_FILENAME in (result.publicacao_aviso or "")
