#!/usr/bin/env python3
"""Append new ZIP uploads to the append-only manifest.jsonl and upload to IA."""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import httpx
import structlog


logger = structlog.get_logger()

IA_CATALOG_ITEM = "causaganha-catalog"
MANIFEST_JSONL_URL = "https://franklinbaldo.github.io/causaganha/manifest.jsonl"
FALLBACK_MANIFEST_URL = "https://archive.org/download/causaganha-catalog/manifest.jsonl"
LOCAL_MANIFEST_PATH = Path("data/manifest.jsonl")
IA_STATE_PATH = Path("data/ia-state.json")


def download_existing_manifest() -> list[dict]:
    """Download existing manifest.jsonl from IA."""
    for url in [MANIFEST_JSONL_URL, FALLBACK_MANIFEST_URL]:
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
    """Extract newly uploaded ZIPs from ia-state.json."""
    if not IA_STATE_PATH.exists():
        logger.warning("ia_state_not_found", path=str(IA_STATE_PATH))
        return []

    try:
        data = json.loads(IA_STATE_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.exception("error_reading_ia_state", error=str(e))
        return []

    entries = data.get("entries", {})
    new_rows = []
    now_str = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")

    for date_str, item_data in entries.items():
        if isinstance(item_data, dict):
            for tribunal, status in item_data.items():
                if status == "uploaded":
                    year = date_str[:4]
                    filename = f"djen-{date_str}-{tribunal.upper()}.zip"
                    item_id = f"djen-{tribunal.lower()}-{year}"
                    row = {
                        "date": date_str,
                        "tribunal": tribunal.upper(),
                        "zip_url": f"https://archive.org/download/{item_id}/{filename}",
                        "downloaded_at": now_str,
                    }
                    new_rows.append(row)

    return new_rows


def upload_to_ia(file_path: Path) -> bool:
    """Upload manifest.jsonl to IA using httpx and S3-like API."""
    access_key = os.environ.get("IA_ACCESS_KEY")
    secret_key = os.environ.get("IA_SECRET_KEY")

    if not access_key or not secret_key:
        logger.error("ia_credentials_missing")
        return False

    url = f"https://s3.us.archive.org/{IA_CATALOG_ITEM}/manifest.jsonl"
    headers = {
        "Authorization": f"LOW {access_key}:{secret_key}",
        "x-archive-interactive-priority": "1",
        "x-amz-auto-make-bucket": "1",
    }

    file_size = file_path.stat().st_size
    headers["Content-Length"] = str(file_size)

    try:
        with file_path.open("rb") as f:
            response = httpx.put(url, headers=headers, content=f, timeout=60.0)

        if response.status_code in (200, 201):
            logger.info("upload_success", item=IA_CATALOG_ITEM, file=file_path.name)
            return True
        logger.error("upload_failed", status=response.status_code, text=response.text[:200])
        return False
    except Exception as e:
        logger.exception("upload_exception", error=str(e))
        return False


def main() -> int:
    logger.info("starting_append_manifest")

    existing_rows = download_existing_manifest()
    logger.info("existing_rows", count=len(existing_rows))

    new_rows = get_new_uploads()
    logger.info("new_rows_from_state", count=len(new_rows))

    if not new_rows:
        logger.info("no_new_rows_to_append")
        # Even if no new rows, we should ensure local manifest exists for downstream
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

    if os.environ.get("IA_ACCESS_KEY"):
        success = upload_to_ia(LOCAL_MANIFEST_PATH)
        if not success:
            logger.error("failed_to_upload_manifest")
            return 1
    else:
        logger.info("skipping_upload_no_credentials")

    return 0


if __name__ == "__main__":
    sys.exit(main())
