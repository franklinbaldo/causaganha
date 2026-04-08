import os
import re
import sys
from pathlib import Path
from typing import Any

import httpx
import structlog


# Ensure we can import from the root
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.pipeline.ia_s3 import create_upload_client, get_ia_s3_auth


logger = structlog.get_logger()

# Constants
DRY_RUN = os.environ.get("CLEANUP_DRY_RUN", "true").lower() == "true"
OLD_PATTERN = re.compile(r"^djen-\d{4}-\d{2}-\d{2}$")
YEARLY_PATTERN = re.compile(r"^djen-[a-z0-9-]+-\d{4}$")


def get_item_metadata(client: httpx.Client, item_id: str) -> dict[str, Any] | None:
    """Fetch item metadata from the IA Metadata API."""
    url = f"https://archive.org/metadata/{item_id}"
    try:
        resp = client.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.exception("metadata_fetch_failed", item_id=item_id, error=str(e))
        return None


def file_exists_in_bucket(client: httpx.Client, bucket_id: str, filename: str) -> bool:
    """Check if a specific filename exists in an IA bucket."""
    meta = get_item_metadata(client, bucket_id)
    if not meta or "files" not in meta:
        return False
    return any(f.get("name") == filename for f in meta["files"])


def delete_ia_file(client: httpx.Client, item_id: str, filename: str) -> bool:
    """Delete a file from an IA item using the S3-compatible API."""
    if DRY_RUN:
        return True

    url = f"https://s3.us.archive.org/{item_id}/{filename}"
    try:
        # IA S3 requires a DELETE request for removal
        resp = client.delete(url)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.exception("file_deletion_failed", item_id=item_id, file=filename, error=str(e))
        return False


def cleanup_deprecated_items():
    auth = get_ia_s3_auth()
    if not auth and not DRY_RUN:
        logger.error(
            "No IA credentials found. Please set IAS3_ACCESS_KEY/SECRET_KEY for actual cleanup."
        )
        return

    # Create client with auth if available, else anonymous for public audit
    client = create_upload_client(auth) if auth else httpx.Client(timeout=30)

    # 1. Find all djen items
    search_url = "https://archive.org/advancedsearch.php"
    params = {"q": "identifier:djen-20*", "fl[]": "identifier", "rows": "1000", "output": "json"}

    logger.info("searching_ia_items", query=params["q"])
    try:
        resp = client.get(search_url, params=params)
        resp.raise_for_status()
        items = resp.json().get("response", {}).get("docs", [])
    except Exception as e:
        logger.exception("ia_search_failed", error=str(e))
        return

    logger.info("items_found", total=len(items))

    processed = 0
    redundant_items = []

    for item in items:
        item_id = item["identifier"]

        # Only process items matching the old daily pattern
        if not OLD_PATTERN.match(item_id):
            continue

        processed += 1
        if processed % 10 == 0:
            logger.info("processing_progress", processed=processed, total=len(items))

        meta = get_item_metadata(client, item_id)
        if not meta or not meta.get("files"):
            continue

        files = meta["files"]

        # --- SAFETY CHECKS ---
        has_parquets = any(f.get("name", "").endswith(".parquet") for f in files)
        has_marker = any("_consolidated" in f.get("name", "") for f in files)

        if has_parquets or has_marker:
            continue

        zips_to_verify = [f.get("name") for f in files if f.get("name", "").endswith(".zip")]
        if not zips_to_verify:
            continue

        redundant_count = 0
        for zip_name in zips_to_verify:
            # zip_name is like "djen-2025-07-31-STJ.zip"
            # we need to find the tribunal and year from this
            parts = zip_name.replace(".zip", "").split("-")
            if len(parts) < 5:  # djen-YYYY-MM-DD-TRIB
                logger.warning("invalid_zip_name_format", file=zip_name)
                continue

            year = parts[1]
            tribunal = parts[4].lower()
            yearly_bucket = f"djen-{tribunal}-{year}"

            # Verify the ZIP exists in the yearly bucket
            if file_exists_in_bucket(client, yearly_bucket, zip_name):
                redundant_count += 1
            else:
                logger.warning("zip_MISSING_in_yearly_bucket", file=zip_name, target=yearly_bucket)
                break

        # --- ACTION ---
        if redundant_count == len(zips_to_verify):
            redundant_items.append(item_id)
            if not DRY_RUN:
                for f in files:
                    fname = f.get("name")
                    delete_ia_file(client, item_id, fname)

    logger.info("cleanup_completed", redundant_identified=len(redundant_items))
    if DRY_RUN:
        logger.info(
            "dry_run_results", redundant_items=redundant_items[:10], note="showing first 10"
        )


if __name__ == "__main__":
    if DRY_RUN:
        print(">>> CLEANUP DRY RUN ENABLED (CLEANUP_DRY_RUN=true) <<<")
    cleanup_deprecated_items()
