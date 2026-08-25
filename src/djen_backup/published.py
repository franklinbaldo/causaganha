"""Strict, bounded reader for the DJEN manifest published on Internet Archive.

This boundary is intentionally different from ``SyncManifest.load_from_ia``.
The engine reader is allowed to degrade after retries so ingestion can continue
from local state; health/status must instead distinguish authoritative absence
from an authority that could not be verified.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterable
from pathlib import Path

import httpx

from djen_backup.manifest import (
    IA_PARQUET_FILENAME,
    IA_STATE_ITEM,
    SyncManifest,
    _read_parquet_rows,
)
from djen_backup.segments import SEGMENT_COMPACTED_DIR, SEGMENT_DIR

_DOWNLOAD_URL = f"https://archive.org/download/{IA_STATE_ITEM}/{{}}"
_FILES_URL = f"https://archive.org/metadata/{IA_STATE_ITEM}/files"
_DEFAULT_TIMEOUT_SECONDS = 10.0


class PublishedManifestUnavailable(RuntimeError):
    """The published DJEN authority exists or is expected but is unverifiable."""


def _response_error(label: str, response: httpx.Response) -> PublishedManifestUnavailable:
    return PublishedManifestUnavailable(f"{label} returned HTTP {response.status_code}")


def _pending_segment_names(payload: object) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("result"), list):
        raise PublishedManifestUnavailable("Internet Archive files metadata is malformed")

    names: list[str] = []
    for item in payload["result"]:
        if not isinstance(item, dict):
            raise PublishedManifestUnavailable("Internet Archive files metadata contains invalid item")
        name = item.get("name")
        if not isinstance(name, str):
            raise PublishedManifestUnavailable("Internet Archive files metadata contains invalid name")
        if (
            name.startswith(f"{SEGMENT_DIR}/")
            and not name.startswith(f"{SEGMENT_COMPACTED_DIR}/")
            and name.endswith(".csv")
        ):
            names.append(name)
    return sorted(names)


def _apply_rows(manifest: SyncManifest, rows: Iterable[tuple]) -> None:
    for row in rows:
        if len(row) != 6:
            raise PublishedManifestUnavailable("published parquet has an unexpected row shape")
        tribunal, day, ia_status, djen_status, djen_raw, updated_at = row
        try:
            manifest.apply_event(
                str(tribunal),
                day,
                ia_status=ia_status or "",
                djen_status=djen_status or "",
                djen_raw=djen_raw or "",
                updated_at=updated_at or "",
            )
        except (TypeError, ValueError) as exc:
            raise PublishedManifestUnavailable(f"published parquet row is invalid: {exc}") from exc


def _apply_segment_strict(manifest: SyncManifest, name: str, text: str) -> None:
    rows = [line for line in text.splitlines() if line.strip() and not line.startswith("tribunal")]
    applied = manifest.apply_segment_csv(text)
    if applied != len(rows):
        raise PublishedManifestUnavailable(
            f"published segment {name!r} is malformed: applied {applied} of {len(rows)} rows"
        )


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
        try:
            parquet = http.get(_DOWNLOAD_URL.format(IA_PARQUET_FILENAME))
        except httpx.HTTPError as exc:
            raise PublishedManifestUnavailable(f"could not read published parquet: {exc}") from exc

        if parquet.status_code == httpx.codes.NOT_FOUND:
            return None
        if parquet.status_code != httpx.codes.OK:
            raise _response_error("published parquet", parquet)

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp.write(parquet.content)
            tmp_path = Path(tmp.name)
        try:
            try:
                rows = _read_parquet_rows(str(tmp_path))
            except Exception as exc:
                raise PublishedManifestUnavailable(f"published parquet is invalid: {exc}") from exc
        finally:
            tmp_path.unlink(missing_ok=True)

        manifest = SyncManifest()
        _apply_rows(manifest, rows)

        try:
            metadata = http.get(_FILES_URL)
        except httpx.HTTPError as exc:
            raise PublishedManifestUnavailable(f"could not verify published segments: {exc}") from exc
        if metadata.status_code != httpx.codes.OK:
            raise _response_error("Internet Archive files metadata", metadata)
        try:
            segment_names = _pending_segment_names(metadata.json())
        except ValueError as exc:
            raise PublishedManifestUnavailable("Internet Archive files metadata is not JSON") from exc

        for name in segment_names:
            try:
                segment = http.get(_DOWNLOAD_URL.format(name))
            except httpx.HTTPError as exc:
                raise PublishedManifestUnavailable(f"could not read published segment {name!r}: {exc}") from exc
            if segment.status_code != httpx.codes.OK:
                raise _response_error(f"published segment {name!r}", segment)
            _apply_segment_strict(manifest, name, segment.text)

        return manifest
    finally:
        if owns_client:
            http.close()
