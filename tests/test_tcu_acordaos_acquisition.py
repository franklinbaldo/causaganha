from __future__ import annotations

import io
from pathlib import Path

import pytest

from tcu_acordaos.acquisition import download_official_csv


class _Response(io.BytesIO):
    def __init__(self, payload: bytes, *, final_url: str) -> None:
        super().__init__(payload)
        self._final_url = final_url

    def geturl(self) -> str:
        return self._final_url

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def test_download_records_size_hash_and_final_url(tmp_path: Path) -> None:
    payload = b"KEY,ACORDAO\nAC-1,conteudo\n"
    url = "https://sites.tcu.gov.br/dados-abertos/jurisprudencia/acordaos.csv"

    evidence = download_official_csv(
        url,
        tmp_path / "acordaos.csv",
        opener=lambda _url: _Response(
            payload,
            final_url="https://cdn.tcu.gov.br/jurisprudencia/acordaos.csv",
        ),
        acquired_at="2026-09-02T15:00:00Z",
    )

    assert (tmp_path / "acordaos.csv").read_bytes() == payload
    assert evidence.source_url == url
    assert evidence.final_url == "https://cdn.tcu.gov.br/jurisprudencia/acordaos.csv"
    assert evidence.acquired_at == "2026-09-02T15:00:00Z"
    assert evidence.size_bytes == len(payload)
    assert evidence.sha256 == "b14a4098d30704e4c691467445b0349f25edbef253127781e8cbf13e388f9cca"


@pytest.mark.parametrize(
    "url",
    [
        "http://sites.tcu.gov.br/acordaos.csv",
        "https://example.org/acordaos.csv",
        "file:///tmp/acordaos.csv",
    ],
)
def test_download_rejects_non_official_urls(tmp_path: Path, url: str) -> None:
    with pytest.raises(ValueError, match="TCU bulk URL"):
        download_official_csv(url, tmp_path / "acordaos.csv")


def test_download_rejects_redirect_outside_tcu_and_keeps_existing_file(tmp_path: Path) -> None:
    destination = tmp_path / "acordaos.csv"
    destination.write_bytes(b"previous")

    with pytest.raises(ValueError, match="hosted on tcu.gov.br"):
        download_official_csv(
            "https://sites.tcu.gov.br/acordaos.csv",
            destination,
            opener=lambda _url: _Response(
                b"untrusted",
                final_url="https://example.org/acordaos.csv",
            ),
        )

    assert destination.read_bytes() == b"previous"
    assert not list(tmp_path.glob(".*.tmp"))


def test_download_is_atomic_when_stream_fails(tmp_path: Path) -> None:
    destination = tmp_path / "acordaos.csv"
    destination.write_bytes(b"previous")

    class BrokenResponse(_Response):
        def read(self, size: int = -1) -> bytes:
            if self.tell() > 0:
                msg = "connection dropped"
                raise OSError(msg)
            return super().read(4 if size == -1 else min(size, 4))

    with pytest.raises(OSError, match="connection dropped"):
        download_official_csv(
            "https://sites.tcu.gov.br/acordaos.csv",
            destination,
            opener=lambda _url: BrokenResponse(
                b"new-content",
                final_url="https://sites.tcu.gov.br/acordaos.csv",
            ),
        )

    assert destination.read_bytes() == b"previous"
    assert not list(tmp_path.glob(".*.tmp"))
