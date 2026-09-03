from __future__ import annotations

import hashlib
from io import BytesIO

import pytest

from tse_processual.acquisition import download_official_zip, validate_official_url
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
            opener=lambda _url: _Response(b"payload", "https://example.org/decisoes.zip"),
        )

    assert not destination.exists()
