"""Publish verified TCU TEOR Parquet artifacts to Internet Archive."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import duckdb
import httpx

from causaganha.pipeline.ia_s3 import meta_value as _meta_value


IA_ITEM_ID = "causaganha-tcu-acordaos"
_IA_S3_BASE = f"https://s3.us.archive.org/{IA_ITEM_ID}"
_IA_PUBLIC_BASE = f"https://archive.org/download/{IA_ITEM_ID}"
_REQUIRED_COLUMNS = frozenset({"key", "source_url", "acquired_at", "source_sha256"})
_FORBIDDEN_COLUMNS = frozenset({"visaogeral"})
_RETRIABLE = frozenset({408, 429, 500, 502, 503, 504})


@dataclass(frozen=True)
class PublicationProof:
    """Evidence that the bytes published by IA match the local product artifact."""

    year: int
    public_url: str
    sha256: str
    size_bytes: int
    records: int
    columns: tuple[str, ...]


def remote_name(year: int) -> str:
    """Return the stable remote filename for one published TCU year."""
    if year < 1900 or year > 9999:
        msg = f"invalid TCU year: {year}"
        raise ValueError(msg)
    return f"tcu-acordaos-teor-{year}.parquet"


def public_url(year: int) -> str:
    """Return the public read URL for one TCU product year."""
    return f"{_IA_PUBLIC_BASE}/{remote_name(year)}"


def _upload_url(year: int) -> str:
    return f"{_IA_S3_BASE}/{remote_name(year)}"


def _upload_headers(ia_key: str, ia_secret: str) -> dict[str, str]:
    return {
        "Authorization": f"LOW {ia_key}:{ia_secret}",
        "Content-Type": "application/octet-stream",
        "x-archive-auto-make-bucket": "1",
        "x-archive-meta-mediatype": "data",
        "x-archive-meta-subject": _meta_value("TCU;acórdãos;TEOR;direito brasileiro"),
        "x-archive-meta-title": _meta_value("TCU Acórdãos — TEOR"),
        "x-archive-meta-description": _meta_value(
            "Artefatos Parquet de TEOR dos acórdãos do Tribunal de Contas da União, "
            "com identidade oficial e proveniência preservadas."
        ),
    }


def sha256_file(path: Path) -> str:
    """Hash a local artifact without loading it entirely into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def upload_parquet(
    path: Path,
    *,
    year: int,
    ia_key: str,
    ia_secret: str,
    max_retries: int = 5,
) -> None:
    """Upload one product artifact using the repository's IA HTTP contract.

    A successful PUT is deliberately not considered publication proof. Call
    :func:`verify_public_parquet` (or :func:`publish_and_verify`) before
    advertising the year as available.
    """
    if path.suffix != ".parquet":
        msg = "TCU publication artifact must end in .parquet"
        raise ValueError(msg)

    headers = _upload_headers(ia_key, ia_secret)
    with httpx.Client(timeout=300) as client:
        for attempt in range(max_retries + 1):
            try:
                with path.open("rb") as stream:
                    response = client.put(_upload_url(year), content=stream, headers=headers)
            except httpx.HTTPError:
                if attempt >= max_retries:
                    raise
                continue

            if 200 <= response.status_code < 300:
                return
            if response.status_code not in _RETRIABLE or attempt >= max_retries:
                response.raise_for_status()

    msg = "Internet Archive upload exhausted retries"
    raise RuntimeError(msg)


def _inspect_parquet(path: Path) -> tuple[int, tuple[str, ...]]:
    path_sql = str(path).replace("'", "''")
    with duckdb.connect() as con:
        rows = con.execute(f"SELECT count(*) FROM read_parquet('{path_sql}')").fetchone()
        if rows is None:
            msg = "could not count remote TCU parquet"
            raise ValueError(msg)
        columns = tuple(
            row[0]
            for row in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path_sql}')").fetchall()
        )
    return int(rows[0]), columns


def verify_public_parquet(
    *,
    year: int,
    expected_sha256: str,
    expected_records: int,
    timeout: float = 300,
) -> PublicationProof:
    """Read the public IA bytes back and validate hash, schema and row count."""
    url = public_url(year)
    digest = hashlib.sha256()
    size_bytes = 0
    fd, tmp_name = tempfile.mkstemp(suffix=".parquet")
    os.close(fd)
    tmp = Path(tmp_name)

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                with tmp.open("wb") as target:
                    for chunk in response.iter_bytes():
                        if not chunk:
                            continue
                        target.write(chunk)
                        digest.update(chunk)
                        size_bytes += len(chunk)

        observed_sha256 = digest.hexdigest()
        if observed_sha256 != expected_sha256:
            msg = (
                "TCU public read-back checksum mismatch: "
                f"expected {expected_sha256}, got {observed_sha256}"
            )
            raise ValueError(msg)

        records, columns = _inspect_parquet(tmp)
        normalized = {column.casefold() for column in columns}
        missing = _REQUIRED_COLUMNS - normalized
        forbidden = _FORBIDDEN_COLUMNS & normalized
        if missing:
            msg = f"TCU public parquet missing required columns: {sorted(missing)}"
            raise ValueError(msg)
        if forbidden:
            msg = f"TCU public parquet contains forbidden columns: {sorted(forbidden)}"
            raise ValueError(msg)
        if records != expected_records:
            msg = (
                "TCU public parquet row-count mismatch: "
                f"expected {expected_records}, got {records}"
            )
            raise ValueError(msg)

        return PublicationProof(
            year=year,
            public_url=url,
            sha256=observed_sha256,
            size_bytes=size_bytes,
            records=records,
            columns=columns,
        )
    finally:
        tmp.unlink(missing_ok=True)


def publish_and_verify(
    path: Path,
    *,
    year: int,
    records: int,
    ia_key: str,
    ia_secret: str,
) -> PublicationProof:
    """Upload and return proof only after successful public read-back."""
    expected_sha256 = sha256_file(path)
    upload_parquet(path, year=year, ia_key=ia_key, ia_secret=ia_secret)
    return verify_public_parquet(
        year=year,
        expected_sha256=expected_sha256,
        expected_records=records,
    )
