import argparse
import logging
import sys
from pathlib import Path

from src.database import CausaGanhaDB
from src.pii_manager import PiiManager
from src.config import load_config  # For potential future config like allow_decoding

# Add project root to sys.path to allow importing from src
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Setup basic logging for the tool
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - DECODE_TOOL - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="""
        Decodes a PII UUID back to its original value.
        WARNING: Accessing original PII is a sensitive operation.
                 Ensure you are authorized and handle the output securely.
        """,
        epilog="Example: python scripts/decode_pii_tool.py <UUID_TO_DECODE>",
    )
    parser.add_argument("pii_uuid", type=str, help="The PII UUID to decode.")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=project_root / "data" / "causaganha.duckdb",  # Default path
        help="Path to the DuckDB database file.",
    )
    parser.add_argument(
        "--requester",
        type=str,
        default="MANUAL_DECODE_TOOL_USER",
        help="Identifier for who is running this tool (for audit logs).",
    )

    args = parser.parse_args()

    # --- Configuration Check for PII Decoding ---
    config = load_config()
    if not config.get("security", {}).get(
        "allow_pii_decoding", False
    ):  # Default to False if not set
        logger.error(
            "PII decoding is disabled in the application configuration (security.allow_pii_decoding = false)."
        )
        print(
            "ERROR: PII decoding is disabled in the application configuration. To enable, set security.allow_pii_decoding = true in your config.toml.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.db_path.exists():
        logger.error(f"Database file not found at: {args.db_path}")
        print(f"ERROR: Database file not found at: {args.db_path}", file=sys.stderr)
        sys.exit(1)

    db = None
    try:
        logger.info(f"Connecting to database: {args.db_path}")
        db = CausaGanhaDB(db_path=args.db_path)
        db.connect()  # This also runs migrations, ensuring pii_decode_map exists

        pii_manager = PiiManager(db.conn)

        logger.info(
            f"Attempting to decode PII UUID: {args.pii_uuid} by requester: {args.requester}"
        )

        decoded_info = pii_manager.get_original_pii(
            args.pii_uuid, requester_info=args.requester
        )

        if decoded_info:
            print("\n--- PII DECODING SUCCESSFUL ---")
            print(f"  UUID: {args.pii_uuid}")
            print(f"  Type: {decoded_info['pii_type']}")
            print(f"  Original Value: {decoded_info['original_value']}")
            print("---------------------------------")
            logger.info(
                f"Successfully decoded and displayed PII for UUID: {args.pii_uuid}"
            )
        else:
            print(
                f"\nERROR: PII UUID '{args.pii_uuid}' not found or could not be decoded."
            )
            logger.warning(f"Failed to decode PII UUID: {args.pii_uuid} - Not found.")
            sys.exit(1)

    except Exception as e:
        logger.error(
            f"An error occurred during the decoding process: {e}", exc_info=True
        )
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if db and db.conn:
            logger.info("Closing database connection.")
            db.close()


if __name__ == "__main__":
    print(
        "WARNING: You are about to run a tool that can expose Personally Identifiable Information (PII)."
    )
    print("Ensure you are authorized and are following all data handling policies.\n")
    # Brief pause or confirmation could be added here if desired
    confirm = input("Press Enter to continue if you are sure, or type 'N' to cancel: ")
    if confirm.lower() == "n":
        logger.info("PII decoding cancelled by user.")
        sys.exit(0)
    main()
