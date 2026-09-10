from __future__ import annotations

import hashlib
from io import BytesIO

import httpx
import pytest

from common.relay import RelayTransport
from tse_processual import acquisition
from tse_processual.acquisition import (
    _default_opener,
    _make_client,
    download_official_zip,
    validate_official_url,
)
from tse_processual.catalog import PROCESSUAL_2026_RESOURCES, ResourceKind, resource_for


class _Response(BytesIO):
    def __init__(self, data: bytes, final_url: str) -> None:
        super().__init__(data)
        self._final_url = final_url

    def geturl(self) -> str:
        return self._final_url


def test_catalog_admits_only_three_non_pii_resources() -> None:
    assert {item.kind for item in PROCESSUAL_2026_RESOURCES} == {
        ResourceKind.PROCESSOS,
        ResourceKind.ASSUNTOS,
        ResourceKind.DECISOES,
    }
    assert all(item.year == 2026 for item in PROCESSUAL_2026_RESOURCES)
    assert all("partes" not in item.url.lower() for item in PROCESSUAL_2026_RESOURCES)


def test_resource_for_rejects_unproven_year() -> None:
    with pytest.raises(ValueError, match="not admitted"):
        resource_for(ResourceKind.PROCESSOS, year=2025)


@pytest.mark.parametrize(
    "url",
    [
        "http://cdn.tse.jus.br/estatistica/sead/odsele/processual/a.zip",
        "https://example.org/estatistica/sead/odsele/processual/a.zip",
        "https://cdn.tse.jus.br/outro/a.zip",
    ],
)
def test_validate_official_url_rejects_non_official_boundaries(url: str) -> None:
    with pytest.raises(ValueError):
        validate_official_url(url)


def test_download_records_checksum_size_and_final_url(tmp_path) -> None:
    payload = b"PK\x03\x04fixture"
    source = resource_for(ResourceKind.PROCESSOS).url
    destination = tmp_path / "processo.zip"

    evidence = download_official_zip(
        source,
        destination,
        opener=lambda _url: _Response(payload, source),
        acquired_at="2026-09-03T03:57:44Z",
    )

    assert destination.read_bytes() == payload
    assert evidence.source_url == source
    assert evidence.final_url == source
    assert evidence.acquired_at == "2026-09-03T03:57:44Z"
    assert evidence.size_bytes == len(payload)
    assert evidence.sha256 == hashlib.sha256(payload).hexdigest()


def test_download_does_not_promote_redirect_outside_tse(tmp_path) -> None:
    source = resource_for(ResourceKind.DECISOES).url
    destination = tmp_path / "decisoes.zip"

    with pytest.raises(ValueError, match="cdn.tse.jus.br"):
        download_official_zip(
            source,
            destination,
            opener=lambda _url: _Response(
                b"payload",
                "https://example.org/decisoes.zip",
            ),
        )

    assert not destination.exists()


# ── relay wiring (issue #985: TSE's Akamai front 403s this sandbox's egress,
# same WAF-block class the relay bypasses for STJ/TJRO) ────────────────────


def test_make_client_routes_through_relay_when_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RELAY_URL", "https://relay.example/")
    monkeypatch.setenv("RELAY_TOKEN", "s3cr3t-token")  # noqa: S105 — test fixture

    assert isinstance(_make_client()._transport, RelayTransport)


def test_make_client_connects_directly_when_relay_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RELAY_URL", raising=False)
    monkeypatch.delenv("RELAY_TOKEN", raising=False)

    assert not isinstance(_make_client()._transport, RelayTransport)


def test_default_opener_streams_bytes_and_reports_final_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"PK\x03\x04fixture-bytes"
    source = resource_for(ResourceKind.PROCESSOS).url

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == source
        return httpx.Response(200, content=payload)

    monkeypatch.setattr(
        acquisition, "_CLIENT", httpx.Client(transport=httpx.MockTransport(handler))
    )

    with _default_opener(source) as response:
        assert response.geturl() == source
        chunks = []
        while chunk := response.read(4):
            chunks.append(chunk)
        assert b"".join(chunks) == payload


def test_default_opener_follows_redirect_and_reports_true_final_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = resource_for(ResourceKind.DECISOES).url
    redirected = "https://cdn.tse.jus.br/estatistica/sead/odsele/processual/moved.zip"
    payload = b"redirected-payload"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == source:
            return httpx.Response(302, headers={"Location": redirected})
        assert str(request.url) == redirected
        return httpx.Response(200, content=payload)

    monkeypatch.setattr(
        acquisition,
        "_CLIENT",
        httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True),
    )

    with _default_opener(source) as response:
        assert response.geturl() == redirected
        assert response.read(len(payload)) == payload


def test_default_opener_relays_transparently_final_url_stays_the_true_destination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Through the relay, geturl() must report the real TSE URL, not the relay URL.

    download_official_zip() calls validate_official_url() on this value — if it
    ever leaked the relay's own URL instead of the true destination, every
    relayed download would fail that check.
    """
    source = resource_for(ResourceKind.ASSUNTOS).url
    payload = b"relayed-payload"
    relay_url = "https://relay.example/"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == relay_url
        assert request.headers["X-Relay-Url"] == source
        return httpx.Response(200, content=payload)

    transport = RelayTransport(
        relay_url,
        "s3cr3t-token",
        inner=httpx.MockTransport(handler),  # noqa: S106
    )
    monkeypatch.setattr(acquisition, "_CLIENT", httpx.Client(transport=transport))

    with _default_opener(source) as response:
        assert response.geturl() == source
        assert response.read(len(payload)) == payload
