import sys
from pathlib import Path

import structlog


# Ensure we can import from the root
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.pipeline.ia_s3 import create_upload_client, get_ia_s3_auth, upload_to_ia


logger = structlog.get_logger()


def fix_metadata(item_id: str, tribunal: str, year: str):
    auth = get_ia_s3_auth()
    if not auth:
        logger.error(
            "No IA credentials found. Run 'ia configure' or set IAS3_ACCESS_KEY/SECRET_KEY."
        )
        return

    client = create_upload_client(auth)

    # We need a dummy file to trigger the metadata update via the S3 API in ia_s3.py
    # because upload_to_ia is designed around uploading a file.
    dummy_path = Path("metadata_update.txt")
    dummy_path.write_text("Metadata last updated by CausaGanha fix script.")

    date_str = f"{year}-01-01"  # Default date for yearly item

    logger.info("updating_metadata", item_id=item_id)

    # upload_to_ia will now use the improved logic to set the title and description
    # because item_id "djen-tjsp-2026" matches the yearly pattern.
    success = upload_to_ia(client=client, item_id=item_id, file_path=dummy_path, date_str=date_str)

    if success:
        logger.info("metadata_updated_successfully", item_id=item_id)
    else:
        logger.error("metadata_update_failed", item_id=item_id)

    if dummy_path.exists():
        dummy_path.unlink()


if __name__ == "__main__":
    # Fix the specific item reported by the user
    fix_metadata("djen-tjsp-2026", "tjsp", "2026")
