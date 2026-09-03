from __future__ import annotations

import hashlib
from pathlib import Path

import duckdb
import httpx
import pytest

from tcu_acordaos import archive


def _write_parquet(path: Path, *, include_visaogeral: bool = False) -> bytes:
    extra = ", 'resumo IA' AS visaogeral" if include_visaogeral else ""
    path_sql = str(path).replace("'", "''")
    with duckdb.connect() as con:
        con.execute(
            "COPY (SELECT 'k1' AS key, 'https://tcu.gov.br/a.csv' AS source_url, "
            "'2026-09-02T00:00:00Z' AS acquired_at, repeat('a', 64) AS source_sha256"
            f"{extra}) TO '{path_sql}' (FORMAT PARQUET)"
        )
    return path.read_bytes()


def test_remote_name_and_public_url_are_stable() -> None:
    assert archive.remote_name(2026) == "tcu-acordaos-teor-2026.parquet"
    assert archive.public_url(2026) == (
        "https://archive.org/download/causaganha-tcu-acordaos/"
        "tcu-acordaos-teor-2026.parquet"
    )


@pytest.mark.parametrize("year", [0, 1899, 10000])
def test_remote_name_rejects_invalid_year(year: int) -> None:
    with pytest.raises(ValueError, match="invalid TCU year"):
        archive.remote_name(year)


def test_upload_uses_ia_http_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = tmp_path / "tcu.parquet"
    artifact.write_bytes(b"parquet-bytes")
    seen: dict[str, object] = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            raise AssertionError("success must not call raise_for_status")

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            seen["client_kwargs"] = kwargs

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def put(self, url: str, *, content: object, headers: dict[str, str]) -> FakeResponse:
            seen["url"] = url
            seen["headers"] = headers
            seen["bytes"] = content.read()  # type: ignore[attr-defined]
            return FakeResponse()

    monkeypatch.setattr(archive.httpx, "Client", FakeClient)

    archive.upload_parquet(
        artifact,
        year=2026,
        ia_key="key",
        ia_secret="secret",
        max_retries=0,
    )

    assert seen["url"] == (
        "https://s3.us.archive.org/causaganha-tcu-acordaos/"
        "tcu-acordaos-teor-2026.parquet"
    )
    headers = seen["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "LOW key:secret"
    assert headers["x-archive-meta-mediatype"] == "data"
    assert seen["bytes"] == b"parquet-bytes"


def test_verify_public_parquet_proves_bytes_schema_and_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.parquet"
    payload = _write_parquet(source)
    expected_sha = hashlib.sha256(payload).hexdigest()
    seen: dict[str, object] = {}

    class FakeStreamResponse:
        def __enter__(self) -> FakeStreamResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self):
            midpoint = len(payload) // 2
            yield payload[:midpoint]
            yield payload[midpoint:]

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            seen["client_kwargs"] = kwargs

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def stream(self, method: str, url: str) -> FakeStreamResponse:
            seen["method"] = method
            seen["url"] = url
            return FakeStreamResponse()

    monkeypatch.setattr(archive.httpx, "Client", FakeClient)

    proof = archive.verify_public_parquet(
        year=2026,
        expected_sha256=expected_sha,
        expected_records=1,
    )

    assert seen["method"] == "GET"
    assert seen["url"] == archive.public_url(2026)
    assert proof.sha256 == expected_sha
    assert proof.size_bytes == len(payload)
    assert proof.records == 1
    assert {"key", "source_url", "acquired_at", "source_sha256"} <= set(proof.columns)


def test_verify_public_parquet_rejects_checksum_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.parquet"
    payload = _write_parquet(source)

    class FakeStreamResponse:
        def __enter__(self) -> FakeStreamResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self):
            yield payload

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def stream(self, method: str, url: str) -> FakeStreamResponse:
            return FakeStreamResponse()

    monkeypatch.setattr(archive.httpx, "Client", FakeClient)

    with pytest.raises(ValueError, match="checksum mismatch"):
        archive.verify_public_parquet(
            year=2026,
            expected_sha256="0" * 64,
            expected_records=1,
        )


def test_inspect_rejects_visaogeral_via_verifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.parquet"
    payload = _write_parquet(source, include_visaogeral=True)
    expected_sha = hashlib.sha256(payload).hexdigest()

    class FakeStreamResponse:
        def __enter__(self) -> FakeStreamResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self):
            yield payload

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def stream(self, method: str, url: str) -> FakeStreamResponse:
            return FakeStreamResponse()

    monkeypatch.setattr(archive.httpx, "Client", FakeClient)

    with pytest.raises(ValueError, match="forbidden columns"):
        archive.verify_public_parquet(
            year=2026,
            expected_sha256=expected_sha,
            expected_records=1,
        )
