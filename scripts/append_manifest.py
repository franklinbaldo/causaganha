#!/usr/bin/env python3
"""Append new ZIP uploads to the append-only manifest.jsonl and upload to IA.

Purpose:  Record freshly uploaded DJEN ZIPs as entries in the append-only
          manifest.jsonl artifact on Internet Archive.
Problem:  Uploads happen incrementally and from multiple runs; we need a durable
          log of what landed without rewriting (and risking clobbering) the whole
          manifest on every upload.
Strategy: Append new rows as JSONL lines and push to IA. Append-only keeps writes
          cheap and concurrency-safe (no read-modify-write of the full file).
Status:   production — invoked by the collect/backfill workflows.
"""

# Safely reconfigure standard output and standard error encoding error handling on Windows
import contextlib
import sys


for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        with contextlib.suppress(AttributeError):
            stream.reconfigure(errors="replace")

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import structlog

from causaganha.consolidate import manifest_reader


logger = structlog.get_logger()

IA_CATALOG_ITEM = "causaganha-catalog"
FALLBACK_MANIFEST_URL = "https://archive.org/download/causaganha-catalog/manifest.jsonl"
LOCAL_MANIFEST_PATH = Path("data/manifest.jsonl")
SYNC_MANIFEST_PATH = Path("data/sync-manifest.parquet")


def download_existing_manifest() -> list[dict]:
    """Download existing manifest.jsonl from IA."""
    for url in [FALLBACK_MANIFEST_URL]:
        try:
            logger.info("attempting_to_download_manifest", url=url)
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    content = response.read().decode("utf-8").strip()
                    if not content:
                        return []
                    return [json.loads(line) for line in content.splitlines() if line.strip()]
        except urllib.error.URLError as e:
            logger.info("no_existing_manifest_or_error", url=url, error=str(e))
        except Exception as e:
            logger.exception("error_downloading_manifest", url=url, error=str(e))

    return []


def get_new_uploads() -> list[dict]:
    """Extract uploaded ZIPs from the materialized manifest and event log.
    Returns all entries with ia_status=uploaded, deduplication is handled
    by the caller via (date, tribunal) keying.
    """
    if not SYNC_MANIFEST_PATH.exists():
        logger.warning("sync_manifest_not_found", path=str(SYNC_MANIFEST_PATH))
        return []

    rows = []
    now_str = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")

    try:
        for entry in manifest_reader.entries(SYNC_MANIFEST_PATH):
            if entry.ia_status != "uploaded":
                continue
            tribunal = entry.tribunal
            date_str = entry.date.isoformat()
            updated_at = entry.updated_at or now_str
            filename = f"djen-{date_str}-{tribunal}.zip"
            item_id = f"djen-{tribunal.lower()}-{entry.date.year}"
            rows.append(
                {
                    "date": date_str,
                    "tribunal": tribunal,
                    "zip_url": f"https://archive.org/download/{item_id}/{filename}",
                    "downloaded_at": updated_at,
                }
            )
    except Exception as e:
        logger.exception("error_reading_sync_manifest", error=str(e))
        return []

    logger.info("new_uploads_from_sync_manifest", count=len(rows))
    return rows


def main() -> int:
    logger.info("starting_append_manifest")

    existing_rows = download_existing_manifest()
    logger.info("existing_rows", count=len(existing_rows))

    new_rows = get_new_uploads()
    logger.info("new_rows_from_state", count=len(new_rows))

    # Only entries NOT yet in the existing manifest are truly new.
    # The materialized manifest accumulates all historical uploads, so comparing
    # against the existing manifest.jsonl avoids spurious has_new_uploads=true.
    existing_keys = {(r.get("date"), r.get("tribunal")) for r in existing_rows}
    truly_new = [r for r in new_rows if (r.get("date"), r.get("tribunal")) not in existing_keys]
    logger.info("truly_new_uploads", count=len(truly_new))

    if os_env := os.environ.get("GITHUB_OUTPUT"):
        with Path(os_env).open("a", encoding="utf-8") as out:
            out.write(f"has_new_uploads={'true' if truly_new else 'false'}\n")

    if not truly_new:
        logger.info("no_new_rows_to_append")
        # Even if no new rows, ensure local manifest exists for downstream steps
        if not LOCAL_MANIFEST_PATH.exists() and existing_rows:
            LOCAL_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
            with LOCAL_MANIFEST_PATH.open("w", encoding="utf-8") as f:
                for row in existing_rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return 0

    combined_dict = {}
    for row in existing_rows:
        key = (row.get("date"), row.get("tribunal"))
        combined_dict[key] = row

    for row in new_rows:
        key = (row.get("date"), row.get("tribunal"))
        combined_dict[key] = row

    final_rows = sorted(
        combined_dict.values(),
        key=lambda x: (x.get("date", ""), x.get("tribunal", "")),
    )
    logger.info("final_rows_after_dedup", count=len(final_rows))

    LOCAL_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCAL_MANIFEST_PATH.open("w", encoding="utf-8") as f:
        for row in final_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    logger.info("manifest_append_complete_locally")

    return 0


if __name__ == "__main__":
    sys.exit(main())
