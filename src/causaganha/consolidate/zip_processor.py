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
from pathlib import Path
from typing import Any

import httpx
import structlog


log = structlog.get_logger()


def download_zip(item_id: str, filename: str, output_path: Path) -> bool:
    """Download ZIP from Internet Archive.

    Streams to disk (no full-file buffering). Raises on HTTP errors —
    callers decide whether to retry or log.
    """
    url = f"https://archive.org/download/{item_id}/{filename}"
    with httpx.stream("GET", url, follow_redirects=True, timeout=300) as response:
        response.raise_for_status()
        with output_path.open("wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)
    return output_path.exists() and output_path.stat().st_size > 0


def stream_zip_to_ndjson(zip_path: Path, ndjson_path: Path) -> int:
    """Extract records from a ZIP and write each as one NDJSON line.

    Returns the number of records written. Never materializes the full
    record set in memory — records are written to disk as they are parsed.

    DJEN ZIPs contain JSON files in a few shapes:
      - top-level array: ``[{...}, {...}]``
      - top-level object with ``items``: ``{"items": [{...}], ...}``
      - single object: ``{...}``
    """
    count = 0
    try:
        with zipfile.ZipFile(zip_path, "r") as zf, ndjson_path.open(
            "w", encoding="utf-8"
        ) as out:
            for name in zf.namelist():
                if not name.endswith(".json"):
                    continue
                try:
                    with zf.open(name) as fh:
                        data = json.load(fh)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

                records_iter = _iter_records(data)
                for rec in records_iter:
                    if not isinstance(rec, dict):
                        continue
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
        except (httpx.HTTPError, httpx.RequestError) as e:
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
        count = stream_zip_to_ndjson(zip_path, ndjson_path)
    except OSError as e:
        log.exception("ndjson_write_failed", file=ndjson_filename, error=str(e))
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
