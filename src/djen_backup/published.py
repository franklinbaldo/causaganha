"""Strict, bounded reader for the DJEN manifest published on Internet Archive.

This boundary is intentionally different from ``SyncManifest.load_from_ia``.
The engine reader is allowed to degrade after retries so ingestion can continue
from local state; health/status must instead distinguish authoritative absence
from an authority that could not be verified.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import httpx

from djen_backup.manifest import IA_PARQUET_FILENAME, IA_STATE_ITEM, SyncManifest
from djen_backup.segments import SEGMENT_COMPACTED_DIR, SEGMENT_DIR


_DOWNLOAD_URL = f"https://archive.org/download/{IA_STATE_ITEM}/{{}}"
_FILES_URL = f"https://archive.org/metadata/{IA_STATE_ITEM}/files"
_DEFAULT_TIMEOUT_SECONDS = 10.0
_PARQUET_ROW_FIELDS = 6


class PublishedManifestUnavailable(RuntimeError):  # noqa: N818
    """The published DJEN authority exists or is expected but is unverifiable."""

    @classmethod
    def response(cls, label: str, status_code: int) -> PublishedManifestUnavailable:
        """Build an error for an unexpected HTTP response."""
        return cls(f"{label} returned HTTP {status_code}")

    @classmethod
    def transport(cls, label: str, exc: Exception) -> PublishedManifestUnavailable:
        """Build an error for a transport or parsing failure."""
        return cls(f"could not {label}: {exc}")

    @classmethod
    def invalid(cls, detail: str) -> PublishedManifestUnavailable:
        """Build an error for invalid published structure."""
        return cls(detail)

    @classmethod
    def malformed_segment(
        cls,
        name: str,
        applied: int,
        expected: int,
    ) -> PublishedManifestUnavailable:
        """Build an error for a segment that could not be fully replayed."""
        return cls(
            f"published segment {name!r} is malformed: applied {applied} of {expected} rows"
        )


@dataclass(frozen=True)
class PublishedComponent:
    """One file that participated in the strict published DJEN observation."""

    name: str
    modified_at: str | None


@dataclass(frozen=True)
class PublishedManifestObservation:
    """Materialized DJEN authority plus publication provenance from the same read."""

    manifest: SyncManifest
    components: tuple[PublishedComponent, ...]

    @property
    def missing_publication_components(self) -> tuple[str, ...]:
        """Return participating components without a verifiable IA modification clock."""
        return tuple(component.name for component in self.components if component.modified_at is None)

    @property
    def latest_publication(self) -> str | None:
        """Return the newest component clock only when every participant is verified."""
        if self.missing_publication_components:
            return None
        return max(component.modified_at for component in self.components if component.modified_at)


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


def _parse_mtime(value: object) -> str | None:
    """Parse Internet Archive file ``mtime`` (Unix seconds) as an aware ISO timestamp."""
    if not isinstance(value, (str, int, float)):
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=UTC).isoformat()
    except (OSError, OverflowError, TypeError, ValueError):
        return None


def _published_components(payload: object) -> tuple[PublishedComponent, ...]:
    """Select the exact parquet + pending segments represented by one IA metadata read."""
    if not isinstance(payload, dict) or not isinstance(payload.get("result"), list):
        detail = "Internet Archive files metadata is malformed"
        raise PublishedManifestUnavailable.invalid(detail)

    file_mtimes: dict[str, str | None] = {}
    pending: list[str] = []
    for item in payload["result"]:
        if not isinstance(item, dict):
            detail = "Internet Archive files metadata contains invalid item"
            raise PublishedManifestUnavailable.invalid(detail)
        name = item.get("name")
        if not isinstance(name, str):
            detail = "Internet Archive files metadata contains invalid name"
            raise PublishedManifestUnavailable.invalid(detail)
        file_mtimes[name] = _parse_mtime(item.get("mtime"))
        if (
            name.startswith(f"{SEGMENT_DIR}/")
            and not name.startswith(f"{SEGMENT_COMPACTED_DIR}/")
            and name.endswith(".csv")
        ):
            pending.append(name)

    names = (IA_PARQUET_FILENAME, *sorted(pending))
    return tuple(PublishedComponent(name=name, modified_at=file_mtimes.get(name)) for name in names)


def _apply_rows(manifest: SyncManifest, rows: list[tuple]) -> None:
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
        label = "read published parquet"
        raise PublishedManifestUnavailable.transport(label, exc) from exc

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
            label = "parse published parquet"
            raise PublishedManifestUnavailable.transport(label, exc) from exc
    finally:
        tmp_path.unlink(missing_ok=True)


def _fetch_components(http: httpx.Client) -> tuple[PublishedComponent, ...]:
    try:
        response = http.get(_FILES_URL)
    except httpx.HTTPError as exc:
        label = "verify published segments"
        raise PublishedManifestUnavailable.transport(label, exc) from exc
    if response.status_code != httpx.codes.OK:
        label = "Internet Archive files metadata"
        raise PublishedManifestUnavailable.response(label, response.status_code)
    try:
        payload = response.json()
    except ValueError as exc:
        detail = "Internet Archive files metadata is not JSON"
        raise PublishedManifestUnavailable.invalid(detail) from exc
    return _published_components(payload)


def _apply_remote_segments(
    http: httpx.Client,
    manifest: SyncManifest,
    components: tuple[PublishedComponent, ...],
) -> None:
    for component in components:
        name = component.name
        if name == IA_PARQUET_FILENAME:
            continue
        try:
            response = http.get(_DOWNLOAD_URL.format(name))
        except httpx.HTTPError as exc:
            label = f"read published segment {name!r}"
            raise PublishedManifestUnavailable.transport(label, exc) from exc
        if response.status_code != httpx.codes.OK:
            label = f"published segment {name!r}"
            raise PublishedManifestUnavailable.response(label, response.status_code)
        _apply_segment_strict(manifest, name, response.text)


def read_published_manifest_observation(
    *,
    client: httpx.Client | None = None,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
) -> PublishedManifestObservation | None:
    """Read the strict DJEN authority and preserve component clocks from that same read.

    ``None`` still has one meaning only: the canonical parquet returned 404.
    Content validity remains strict. Missing or malformed ``mtime`` does not
    invalidate readable content; it makes only the publication clock unknown.
    """
    owns_client = client is None
    http = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)
    try:
        rows = _fetch_parquet_rows(http)
        if rows is None:
            return None
        components = _fetch_components(http)
        manifest = SyncManifest()
        _apply_rows(manifest, rows)
        _apply_remote_segments(http, manifest, components)
        return PublishedManifestObservation(manifest=manifest, components=components)
    finally:
        if owns_client:
            http.close()


def read_published_manifest(
    *,
    client: httpx.Client | None = None,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
) -> SyncManifest | None:
    """Read the canonical published DJEN materialization without silent degradation.

    Compatibility wrapper for existing content consumers. Publication-aware
    callers should use :func:`read_published_manifest_observation` so the exact
    component clocks observed alongside the manifest are not discarded.
    """
    observation = read_published_manifest_observation(
        client=client,
        timeout_seconds=timeout_seconds,
    )
    return observation.manifest if observation is not None else None
