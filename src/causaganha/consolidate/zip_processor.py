"""Download DJEN ZIPs and stream-extract JSON records to NDJSON files.

Key memory fix vs old ``consolidate.py``: the previous
``extract_json_from_zip()`` loaded all JSON records from a ZIP into a Python
list, then the caller iterated it to write NDJSON. For tribunals with large
ZIPs (~50 MB compressed, ~200 MB uncompressed JSON) this doubled peak RAM.

Now ``stream_zip_to_ndjson()`` pipes records directly from the ZIP to the
NDJSON file, one at a time. Peak RAM stays bounded by the largest single
JSON file inside the ZIP (typically a few MB).
"""

from __future__ import annotations

import contextlib
import json
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

import httpx
import structlog

from causaganha.consolidate.validation import validate_ndjson_record


log = structlog.get_logger()


class ZipBudgetExceededError(ValueError):
    """A ZIP archive or one of its members violates an ingestion resource budget.

    Raised for member-count/size/compression-ratio bombs and for unsafe
    (path-escaping) entry names — see TM-05 in docs/SECURITY_THREAT_MODEL.md.
    Distinct from a genuinely empty or corrupt archive: callers must not
    treat this as "0 records", it is a budget violation to log and skip.
    """


class DownloadTooLargeError(OSError):
    """A streamed download exceeded its configured byte budget."""


# Resource budgets against decompression bombs and unbounded downloads
# (TM-05). DJEN ZIPs are one-tribunal-one-day bundles: a handful of JSON
# files per archive, each typically a few MB uncompressed (see module
# docstring). These ceilings are generous multiples of that real shape, not
# tuned tightly to it — they exist to fail closed on adversarial shapes, not
# to constrain legitimate DJEN traffic.
MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024
MAX_ZIP_MEMBERS = 2_000
MAX_MEMBER_COMPRESSED_BYTES = 100 * 1024 * 1024
MAX_MEMBER_UNCOMPRESSED_BYTES = 300 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200
MAX_TOTAL_UNCOMPRESSED_BYTES = 500 * 1024 * 1024


def _is_safe_member_name(name: str) -> bool:
    """Reject ZIP member names that could escape the archive root.

    We never extract members to the filesystem by name (``zf.open`` reads
    into memory keyed on the ``ZipInfo`` object), so this isn't a path
    traversal write vector today — but a name is still adversarial input,
    and failing closed on it costs nothing.
    """
    if "\\" in name:
        return False
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts


def _check_member_budget(info: zipfile.ZipInfo, zip_path: Path) -> None:
    def _raise(reason: str) -> None:
        msg = f"{zip_path}: member {info.filename!r} {reason}"
        raise ZipBudgetExceededError(msg)

    if not _is_safe_member_name(info.filename):
        _raise("has an unsafe member name")
    if info.compress_size > MAX_MEMBER_COMPRESSED_BYTES:
        _raise(
            f"compressed size {info.compress_size} exceeds budget of "
            f"{MAX_MEMBER_COMPRESSED_BYTES} bytes"
        )
    if info.file_size > MAX_MEMBER_UNCOMPRESSED_BYTES:
        _raise(
            f"uncompressed size {info.file_size} exceeds budget of "
            f"{MAX_MEMBER_UNCOMPRESSED_BYTES} bytes"
        )
    if info.compress_size > 0:
        ratio = info.file_size / info.compress_size
        if ratio > MAX_COMPRESSION_RATIO:
            _raise(f"compression ratio {ratio:.1f}x exceeds budget of {MAX_COMPRESSION_RATIO}x")


def _safe_basename(value: str, *, label: str) -> str:
    """Guard a filename/tribunal used to compose a temp-file path.

    Both come from ZIP-listing metadata (IA item listings, DJEN responses)
    that this process doesn't fully control — a value containing a path
    separator or ``..`` must never reach a ``Path(...) / value`` join.
    """
    if not value or "/" in value or "\\" in value or value in {".", ".."}:
        msg = f"unsafe {label}: {value!r}"
        raise ZipBudgetExceededError(msg)
    return value


def download_zip(
    item_id: str,
    filename: str,
    output_path: Path,
    *,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
) -> bool:
    """Download ZIP from Internet Archive.

    Streams to disk (no full-file buffering) and aborts once ``max_bytes``
    is exceeded, deleting the partial file — an unbounded download from a
    compromised/misbehaving source must not fill runner disk (TM-05).
    Raises on HTTP errors — callers decide whether to retry or log.
    """

    def _raise_too_large(written: int) -> None:
        msg = f"download of {item_id}/{filename} exceeded {max_bytes} byte budget"
        raise DownloadTooLargeError(msg)

    url = f"https://archive.org/download/{item_id}/{filename}"
    written = 0
    with httpx.stream("GET", url, follow_redirects=True, timeout=300) as response:
        response.raise_for_status()
        try:
            with output_path.open("wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    written += len(chunk)
                    if written > max_bytes:
                        _raise_too_large(written)
                    f.write(chunk)
        except DownloadTooLargeError:
            output_path.unlink(missing_ok=True)
            raise
    return output_path.exists() and output_path.stat().st_size > 0


def stream_zip_to_ndjson(zip_path: Path, ndjson_path: Path, tribunal: str) -> int:
    """Extract records from a ZIP and write each as one NDJSON line.

    Stamps ``_tribunal`` into every record so downstream transforms can use
    it directly without parsing it back out of the filename.

    Returns the number of records written. Never materializes the full
    record set in memory — records are written to disk as they are parsed.

    Enforces the resource budgets in this module (member count, per-member
    compressed/uncompressed size, compression ratio, total uncompressed
    size, member name safety) before decompressing or loading a member —
    raises ``ZipBudgetExceededError`` rather than returning a low/zero
    count, so a bomb is never mistaken for an empty dataset (TM-05).

    DJEN ZIPs contain JSON files in a few shapes:
      - top-level array: ``[{...}, {...}]``
      - top-level object with ``items``: ``{"items": [{...}], ...}``
      - single object: ``{...}``
    """
    count = 0
    try:
        with zipfile.ZipFile(zip_path, "r") as zf, ndjson_path.open("w", encoding="utf-8") as out:
            infos = zf.infolist()
            if len(infos) > MAX_ZIP_MEMBERS:
                msg = f"{zip_path}: {len(infos)} members exceeds budget of {MAX_ZIP_MEMBERS}"
                raise ZipBudgetExceededError(msg)

            total_uncompressed = 0
            for info in infos:
                if not info.filename.endswith(".json"):
                    continue
                _check_member_budget(info, zip_path)
                total_uncompressed += info.file_size
                if total_uncompressed > MAX_TOTAL_UNCOMPRESSED_BYTES:
                    msg = (
                        f"{zip_path}: total uncompressed size exceeds budget of "
                        f"{MAX_TOTAL_UNCOMPRESSED_BYTES} bytes"
                    )
                    raise ZipBudgetExceededError(msg)

                try:
                    with zf.open(info) as fh:
                        data = json.load(fh)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

                records_iter = _iter_records(data)
                for rec in records_iter:
                    if not isinstance(rec, dict):
                        continue
                    if not validate_ndjson_record(rec):
                        log.warning("invalid_record_discarded", rec_id=rec.get("id"))
                        continue
                    rec["_tribunal"] = tribunal
                    try:
                        line = json.dumps(rec, default=str, ensure_ascii=False)
                    except (TypeError, ValueError):
                        # Skip unserializable records rather than corrupting NDJSON
                        continue
                    # Validate no embedded newlines (would break NDJSON format)
                    if "\n" in line:
                        line = line.replace("\n", " ")
                    out.write(line)
                    out.write("\n")
                    count += 1
    except zipfile.BadZipFile:
        log.warning("bad_zip_file", path=str(zip_path))
    return count


def _iter_records(data: Any) -> list[Any]:
    """Return records from a parsed JSON blob, tolerant of shape variants.

    DJEN ZIPs ship JSON in several shapes:
      - top-level array of records
      - top-level object with ``items`` list
      - single record object
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list):
            return items
        return [data]
    return []


def process_zip_entry(
    zip_entry: dict[str, Any],
    tmp_path: Path,
    ndjson_dir: Path,
    default_item_id: str,
    *,
    local_zips: str | None = None,
) -> tuple[int, int]:
    """Download or copy a ZIP, stream-extract to NDJSON, clean up.

    Returns ``(success_count, records_count)`` — success_count is 1 if
    the ZIP was processed (even if it had 0 records), 0 on failure.
    """
    filename = str(zip_entry["filename"])
    tribunal = str(zip_entry["tribunal"])

    log.info("processing_zip_start", filename=filename, tribunal=tribunal)

    try:
        _safe_basename(filename, label="filename")
        _safe_basename(tribunal, label="tribunal")
    except ZipBudgetExceededError as e:
        log.warning("unsafe_zip_entry_metadata", filename=filename, tribunal=tribunal, error=str(e))
        return 0, 0

    zip_path = tmp_path / filename

    # Download or copy
    if local_zips and "local_path" in zip_entry:
        try:
            shutil.copy2(zip_entry["local_path"], zip_path)
        except OSError as e:
            log.warning("local_copy_failed", filename=filename, error=str(e))
            return 0, 0
    else:
        download_item = str(zip_entry.get("item_id") or default_item_id)
        try:
            ok = download_zip(download_item, filename, zip_path)
        except (httpx.HTTPError, httpx.RequestError, DownloadTooLargeError) as e:
            log.warning("download_failed", filename=filename, error=str(e))
            return 0, 0
        if not ok:
            log.warning("download_failed", filename=filename)
            return 0, 0

    # Stream-extract records → NDJSON
    zip_stem = Path(filename).stem
    ndjson_filename = f"{tribunal}__{zip_stem}.ndjson"
    ndjson_path = ndjson_dir / ndjson_filename

    try:
        count = stream_zip_to_ndjson(zip_path, ndjson_path, tribunal)
    except OSError as e:
        log.exception("ndjson_write_failed", file=ndjson_filename, error=str(e))
        return 0, 0
    except ZipBudgetExceededError as e:
        log.warning("zip_budget_exceeded", filename=filename, tribunal=tribunal, error=str(e))
        with contextlib.suppress(OSError):
            zip_path.unlink()
        with contextlib.suppress(OSError):
            ndjson_path.unlink(missing_ok=True)
        return 0, 0

    if count == 0:
        log.warning("no_records_found", filename=filename)
        with contextlib.suppress(OSError):
            ndjson_path.unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            zip_path.unlink()
        return 0, 0

    with contextlib.suppress(OSError):
        zip_path.unlink()

    return 1, count
