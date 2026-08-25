"""Strict, bounded reader for the DJEN manifest published on Internet Archive.

This boundary is intentionally different from ``SyncManifest.load_from_ia``.
The engine reader is allowed to degrade after retries so ingestion can continue
from local state; health/status must instead distinguish authoritative absence
from an authority that could not be verified.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb
import httpx

from djen_backup.manifest import IA_PARQUET_FILENAME, IA_STATE_ITEM, SyncManifest
from djen_backup.segments import SEGMENT_COMPACTED_DIR, SEGMENT_DIR

if TYPE_CHECKING:
    from collections.abc import Iterable

_DOWNLOAD_URL = f"https://archive.org/download/{IA_STATE_ITEM}/{{}}"
_FILES_URL = f"https://archive.org/metadata/{IA_STATE_ITEM}/files"
_DEFAULT_TIMEOUT_SECONDS = 10.0
_PARQUET_ROW_FIELDS = 6


class PublishedManifestUnavailable(RuntimeError):  # noqa: N818
    """The published DJEN authority exists or is expected but is unverifiable."""

    @classmethod
    def response(cls, label: str, status_code: int) -> PublishedManifestUnavailable:
        return cls(f"{label} returned HTTP {status_code}")

    @classmethod
    def transport(cls, label: str, exc: Exception) -> PublishedManifestUnavailable:
        return cls(f"could not {label}: {exc}")

    @classmethod
    def invalid(cls, detail: str) -> PublishedManifestUnavailable:
        return cls(detail)

    @classmethod
    def malformed_segment(
        cls,
        name: str,
        applied: int,
        expected: int,
    ) -> PublishedManifestUnavailable:
        return cls(
            f"published segment {name!r} is malformed: applied {applied} of {expected} rows"
        )


def _read_parquet_rows(path: Path) -> list[tuple]:
    connection = duckdb.connect()
    try:
        return connection.execute(
            "SELECT tribunal, date, ia_status, djen_status, djen_raw, updated_at "
            "FROM read_parquet(?)",
            [str(path)],
        ).fetchall()
    finally:
        connection.close()


def _pending_segment_names(payload: object) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("result"), list):
        detail = "Internet Archive files metadata is malformed"
        raise PublishedManifestUnavailable.invalid(detail)

    names: list[str] = []
    for item in payload["result"]:
        if not isinstance(item, dict):
            detail = "Internet Archive files metadata contains invalid item"
            raise PublishedManifestUnavailable.invalid(detail)
        name = item.get("name")
        if not isinstance(name, str):
            detail = "Internet Archive files metadata contains invalid name"
            raise PublishedManifestUnavailable.invalid(detail)
        if (
            name.startswith(f"{SEGMENT_DIR}/")
            and not name.startswith(f"{SEGMENT_COMPACTED_DIR}/")
            and name.endswith(".csv")
        ):
            names.append(name)
    return sorted(names)


def _apply_rows(manifest: SyncManifest, rows: Iterable[tuple]) -> None:
    for row in rows:
        if len(row) != _PARQUET_ROW_FIELDS:
            detail = "published parquet has an unexpected row shape"
            raise PublishedManifestUnavailable.invalid(detail)
        tribunal, day, ia_status, djen_status, djen_raw, updated_at = row
        manifest.apply_event(
            str(tribunal),
            day,
            ia_status=ia_status or "",
            djen_status=djen_status or "",
            djen_raw=djen_raw or "",
            updated_at=updated_at or "",
        )


def _apply_segment_strict(manifest: SyncManifest, name: str, text: str) -> None:
    rows = [line for line in text.splitlines() if line.strip() and not line.startswith("tribunal")]
    applied = manifest.apply_segment_csv(text)
    if applied != len(rows):
        raise PublishedManifestUnavailable.malformed_segment(name, applied, len(rows))


def _fetch_parquet_rows(http: httpx.Client) -> list[tuple] | None:
    try:
        response = http.get(_DOWNLOAD_URL.format(IA_PARQUET_FILENAME))
    except httpx.HTTPError as exc:
        raise PublishedManifestUnavailable.transport("read published parquet", exc) from exc

    if response.status_code == httpx.codes.NOT_FOUND:
        return None
    if response.status_code != httpx.codes.OK:
        label = "published parquet"
        raise PublishedManifestUnavailable.response(label, response.status_code)

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp.write(response.content)
        tmp_path = Path(tmp.name)
    try:
        try:
            return _read_parquet_rows(tmp_path)
        except (duckdb.Error, OSError, ValueError) as exc:
            raise PublishedManifestUnavailable.transport(
                "parse published parquet",
                exc,
            ) from exc
    finally:
        tmp_path.unlink(missing_ok=True)


def _fetch_segment_names(http: httpx.Client) -> list[str]:
    try:
        response = http.get(_FILES_URL)
    except httpx.HTTPError as exc:
        raise PublishedManifestUnavailable.transport(
            "verify published segments",
            exc,
        ) from exc
    if response.status_code != httpx.codes.OK:
        label = "Internet Archive files metadata"
        raise PublishedManifestUnavailable.response(label, response.status_code)
    try:
        payload = response.json()
    except ValueError as exc:
        detail = "Internet Archive files metadata is not JSON"
        raise PublishedManifestUnavailable.invalid(detail) from exc
    return _pending_segment_names(payload)


def _apply_remote_segments(http: httpx.Client, manifest: SyncManifest, names: Iterable[str]) -> None:
    for name in names:
        try:
            response = http.get(_DOWNLOAD_URL.format(name))
        except httpx.HTTPError as exc:
            label = f"read published segment {name!r}"
            raise PublishedManifestUnavailable.transport(label, exc) from exc
        if response.status_code != httpx.codes.OK:
            label = f"published segment {name!r}"
            raise PublishedManifestUnavailable.response(label, response.status_code)
        _apply_segment_strict(manifest, name, response.text)


def read_published_manifest(
    *,
    client: httpx.Client | None = None,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
) -> SyncManifest | None:
    """Read the canonical published DJEN materialization without silent degradation.

    ``None`` has one meaning only: the canonical parquet itself returned 404,
    so no published DJEN manifest exists. Transport errors, 5xx responses,
    malformed parquet/files metadata, and unavailable expected segments raise
    :class:`PublishedManifestUnavailable`.
    """
    owns_client = client is None
    http = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)
    try:
        rows = _fetch_parquet_rows(http)
        if rows is None:
            return None
        manifest = SyncManifest()
        _apply_rows(manifest, rows)
        _apply_remote_segments(http, manifest, _fetch_segment_names(http))
        return manifest
    finally:
        if owns_client:
            http.close()
