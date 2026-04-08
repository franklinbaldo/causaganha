import os
import re
import sys
from pathlib import Path

import httpx
import structlog


# Ensure we can import from the root
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.pipeline.ia_s3 import create_upload_client, get_ia_s3_auth, upload_to_ia


logger = structlog.get_logger()

# Constants
DRY_RUN = os.environ.get("METADATA_DRY_RUN", "true").lower() == "true"
# Yearly identifier regex pattern: djen-{tribunal}-{year}
YEARLY_PATTERN = re.compile(r"^djen-([a-z0-9-]+)-(\d{4})$")


def fix_metadata_bulk():
    auth = get_ia_s3_auth()
    if not auth and not DRY_RUN:
        logger.error("No IA credentials found. Please set IAS3_ACCESS_KEY/SECRET_KEY.")
        return

    client = create_upload_client(auth) if auth else httpx.Client(timeout=30)

    if DRY_RUN:
        logger.info(">>> METADATA FIX DRY RUN ENABLED (METADATA_DRY_RUN=true) <<<")

    # 1. Find all potential yearly djen items via advanced search
    search_url = "https://archive.org/advancedsearch.php"
    # We search for items starting with djen- and having CausaGanha as creator
    params = {
        "q": 'identifier:djen-* AND (creator:"CausaGanha" OR creator:"franklinbaldo")',
        "fl[]": "identifier",
        "rows": "1000",
        "output": "json",
    }

    logger.info("searching_ia_items", query=params["q"])
    try:
        resp = client.get(search_url, params=params)
        resp.raise_for_status()
        items = resp.json().get("response", {}).get("docs", [])
    except Exception as e:
        logger.exception("ia_search_failed", error=str(e))
        return

    matched_items = []
    for item in items:
        match = YEARLY_PATTERN.match(item["identifier"])
        if match:
            matched_items.append(
                {
                    "identifier": item["identifier"],
                    "tribunal": match.group(1).upper(),
                    "year": match.group(2),
                }
            )

    logger.info("yearly_buckets_found", count=len(matched_items))

    # --- ACTION ---
    if not DRY_RUN:
        dummy_path = Path("metadata_refresh.txt")
        dummy_path.write_text("Metadata refreshed by CausaGanha bulk correction script.")
    else:
        dummy_path = None

    processed = 0
    updated = 0
    failed = 0

    for item in matched_items:
        item_id = item["identifier"]
        date_str = f"{item['year']}-01-01"

        if DRY_RUN:
            continue

        processed += 1
        if processed % 10 == 0:
            logger.info(
                "metadata_fix_progress",
                processed=processed,
                total=len(matched_items),
                updated=updated,
                failed=failed,
            )

        # upload_to_ia already contains the smart logic to detect it's a yearly
        # bucket and format the title/description correctly.
        success = upload_to_ia(
            client=client, item_id=item_id, file_path=dummy_path, date_str=date_str
        )

        if success:
            updated += 1
        else:
            failed += 1

    logger.info("bulk_metadata_fix_completed", processed=processed, updated=updated, failed=failed)

    # Cleanup
    if dummy_path and dummy_path.exists():
        dummy_path.unlink()


if __name__ == "__main__":
    if DRY_RUN:
        print(">>> METADATA FIX DRY RUN ENABLED (METADATA_DRY_RUN=true) <<<")
    fix_metadata_bulk()
