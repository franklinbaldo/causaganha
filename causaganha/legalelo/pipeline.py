import argparse
import logging
import datetime
import pathlib
import sys
from pythonjsonlogger import jsonlogger # Added

# Adjust sys.path (commented out as primary execution is via -m)
# sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

# Relative imports for module execution
try:
    from .downloader import fetch_tjro_pdf
    from .extractor import GeminiExtractor
    from .elo import update_elo, expected_score
except ImportError as e:
    if __package__ is None or __package__ == '':
        logging.warning(f"Attempting fallback import for direct script execution: {e}")
        from downloader import fetch_tjro_pdf
        from extractor import GeminiExtractor
        from elo import update_elo, expected_score
    else:
        # Log to standard logger before JSON logging is set up if this critical import fails
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Relative import failed even when __package__ is set: {__package__}, Error: {e}")
        raise

# Module-level logger - will be configured by setup_logging
logger = logging.getLogger(__name__)

# Default paths defined at module level
BASE_DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"
DEFAULT_DIARIOS_DIR = BASE_DATA_DIR / "diarios"
DEFAULT_JSON_DIR = BASE_DATA_DIR / "json"
DEFAULT_RATINGS_FILE = BASE_DATA_DIR / "ratings.csv"
DEFAULT_MATCHES_FILE = BASE_DATA_DIR / "partidas.csv"

def setup_logging(is_verbose: bool):
    """Configures structured JSON logging for the application."""
    root_logger = logging.getLogger()

    # Clear any existing handlers
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    handler = logging.StreamHandler()
    # Example format: %(asctime)s %(levelname)s %(name)s %(module)s %(funcName)s %(lineno)d %(message)s
    # JsonFormatter automatically picks up many LogRecord attributes.
    # We can specify a subset or add more via 'rename_fields' or 'static_fields'.
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(module)s %(funcName)s %(lineno)d %(message)s'
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    if is_verbose:
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)

def handle_collect(args):
    logger.info("Handling command", extra={'command': 'collect', 'date': args.date})

    try:
        target_date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
        logger.debug("Parsed date string to date object", extra={'date_string': args.date, 'parsed_date': target_date.isoformat()})
    except ValueError:
        logger.error("Invalid date format for --date", extra={'date_string': args.date, 'expected_format': 'YYYY-MM-DD'})
        return None

    pdf_filename = f"dj_{target_date.strftime('%Y-%m-%d')}.pdf"
    expected_pdf_path_for_log = DEFAULT_DIARIOS_DIR / pdf_filename

    logger.info("Attempting to collect Diário Oficial", extra={'target_date': target_date.isoformat(), 'expected_dir': str(DEFAULT_DIARIOS_DIR)})

    if args.dry_run:
        logger.info("Dry-run: Would call fetch_tjro_pdf", extra={'target_date': target_date.isoformat(), 'expected_path': str(expected_pdf_path_for_log)})
        return str(expected_pdf_path_for_log)

    try:
        downloaded_pdf_path = fetch_tjro_pdf(target_date)
        if downloaded_pdf_path and downloaded_pdf_path.exists():
            logger.info("PDF downloaded successfully", extra={'file_path': str(downloaded_pdf_path)})
            return str(downloaded_pdf_path)
        elif downloaded_pdf_path:
            logger.error("fetch_tjro_pdf reported path but file not found",
                         extra={'reported_path': str(downloaded_pdf_path), 'target_date': target_date.isoformat()})
            return None
        else:
            logger.warning("Failed to download PDF, fetch_tjro_pdf returned None", extra={'target_date': target_date.isoformat()})
            return None
    except Exception as e:
        logger.error("Unexpected error during PDF download",
                     extra={'target_date': target_date.isoformat(), 'error': str(e)}, exc_info=True)
        return None

def handle_extract(args):
    logger.info("Handling command", extra={'command': 'extract', 'pdf_file': str(args.pdf_file)})

    pdf_to_process = pathlib.Path(args.pdf_file)
    output_dir = args.json_output_dir

    if args.dry_run:
        logger.info("Dry-run: (extract stage) Received PDF path. Assuming valid for dry run flow.",
                    extra={'pdf_path': str(pdf_to_process)})
        logger.info("Dry-run: Would initialize GeminiExtractor and call extract_and_save_json",
                    extra={'pdf_file': str(pdf_to_process), 'output_dir': str(output_dir)})
        simulated_json_name = pdf_to_process.stem + ".json"
        return str(output_dir / simulated_json_name)

    if not pdf_to_process.exists() or not pdf_to_process.is_file():
        logger.error("PDF file not found or is not a file", extra={'pdf_path': str(pdf_to_process)})
        return None

    logger.info("Attempting to extract data from PDF",
                extra={'pdf_file': str(pdf_to_process), 'output_dir': str(output_dir)})

    try:
        extractor_instance = GeminiExtractor()
        saved_json_path = extractor_instance.extract_and_save_json(pdf_to_process, output_dir)

        if saved_json_path and saved_json_path.exists():
            logger.info("JSON extracted and saved successfully", extra={'json_file_path': str(saved_json_path)})
            return str(saved_json_path)
        elif saved_json_path:
            logger.error("Extractor reported success but JSON file not found",
                         extra={'reported_path': str(saved_json_path), 'pdf_file': str(pdf_to_process)})
            return None
        else:
            logger.warning("Failed to extract data from PDF, extractor returned None",
                           extra={'pdf_file': str(pdf_to_process)})
            return None
    except Exception as e:
        logger.error("Unexpected error during data extraction",
                     extra={'pdf_file': str(pdf_to_process), 'error': str(e)}, exc_info=True)
        return None

def handle_update(args):
    logger.info("Handling command (placeholder)", extra={'command': 'update'})

    log_payload = {
        'json_dir': str(args.json_dir),
        'ratings_file': str(args.ratings_file),
        'matches_file': str(args.matches_file)
    }
    logger.info("Elo update parameters", extra=log_payload)

    if not args.json_dir.exists() or not args.json_dir.is_dir():
        logger.warning("JSON data directory not found. If this were a real run, no data to process.",
                       extra={'json_dir': str(args.json_dir)})

    if args.dry_run:
        logger.info("Dry-run: Would iterate JSONs, process matches, update Elo ratings.", extra={'dry_run_details': 'No actual Elo logic implemented or executed.'})
        return True

    logger.warning("Placeholder for Elo update logic. NO ACTUAL UPDATES WILL BE PERFORMED.",
                   extra={'status': 'placeholder_not_implemented'})
    # Detailed placeholder info can remain as multi-line in message or be summarized for JSON
    logger.info("Full implementation would involve: reading CSVs, processing JSONs, calculating Elo, writing CSVs.")
    return True

def handle_run(args):
    run_context = {'command': 'run', 'date': args.date, 'dry_run': args.dry_run}
    logger.info("Handling full pipeline run", extra=run_context)
    if args.dry_run:
        logger.info("Dry-run: Orchestrating collect, extract, and update steps.", extra=run_context)

    # --- 1. Collect Stage ---
    logger.info("--- Stage 1: Collect ---", extra=run_context)
    collect_args = argparse.Namespace(date=args.date, dry_run=args.dry_run)
    pdf_path_str = handle_collect(collect_args)

    if not pdf_path_str:
        logger.error("Collect stage failed. Aborting run command.", extra=run_context)
        return False

    logger.info("Collect stage successful", extra={**run_context, 'stage': 'collect', 'pdf_path': pdf_path_str})
    pdf_path = pathlib.Path(pdf_path_str)

    # --- 2. Extract Stage ---
    logger.info("--- Stage 2: Extract ---", extra=run_context)
    extract_args = argparse.Namespace(pdf_file=pdf_path, json_output_dir=DEFAULT_JSON_DIR, dry_run=args.dry_run)
    json_path_str = handle_extract(extract_args)

    if not json_path_str:
        logger.error("Extract stage failed. Aborting run command.", extra=run_context)
        return False

    logger.info("Extract stage successful", extra={**run_context, 'stage': 'extract', 'json_path': json_path_str})

    # --- 3. Update Stage (Placeholder) ---
    logger.info("--- Stage 3: Update (Placeholder) ---", extra=run_context)
    update_args = argparse.Namespace(json_dir=DEFAULT_JSON_DIR, ratings_file=DEFAULT_RATINGS_FILE, matches_file=DEFAULT_MATCHES_FILE, dry_run=args.dry_run)
    update_success = handle_update(update_args)

    if not update_success:
        logger.warning("Update (placeholder) stage reported an issue.", extra={**run_context, 'stage': 'update', 'status': 'issue_reported'})

    logger.info("Update (placeholder) stage completed.", extra={**run_context, 'stage': 'update'})
    logger.info("Full pipeline run completed successfully.", extra=run_context)
    return True

def main():
    # Preliminary parser for global flags like --verbose for early logging setup
    pre_parser = argparse.ArgumentParser(add_help=False) # No help for this one, it's internal
    pre_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging for setup."
    )
    # Parse known args to get --verbose status for logging setup
    logging_args, _ = pre_parser.parse_known_args()
    setup_logging(logging_args.verbose) # Setup logging based on --verbose

    # Main parser
    parser = argparse.ArgumentParser(
        description="CausaGanha Pipeline: Orchestrates PDF collection, data extraction, and Elo rating updates.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    # Add global arguments to the main parser as well for help text and final argument parsing
    parser.add_argument(
        "--verbose", action="store_true", help="Increase output verbosity (set logging level to DEBUG)."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Log actions that would be taken without actually executing them."
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    collect_parser = subparsers.add_parser("collect", help="Download Diário Oficial PDF for a given date.")
    collect_parser.add_argument("--date", type=str, required=True, help="The date for which to download the Diário, in YYYY-MM-DD format.")

    extract_parser = subparsers.add_parser("extract", help="Extract data from a given PDF file.")
    extract_parser.add_argument("--pdf_file", type=pathlib.Path, required=True, help="Path to the PDF file to process.")
    extract_parser.add_argument("--json_output_dir", type=pathlib.Path, default=DEFAULT_JSON_DIR, help=f"Directory to save the extracted JSON file. Defaults to {DEFAULT_JSON_DIR}")

    update_parser = subparsers.add_parser("update", help="Update Elo ratings based on extracted data (placeholder).")
    update_parser.add_argument("--json_dir", type=pathlib.Path, default=DEFAULT_JSON_DIR, help=f"Directory containing JSON files. Defaults to {DEFAULT_JSON_DIR}")
    update_parser.add_argument("--ratings_file", type=pathlib.Path, default=DEFAULT_RATINGS_FILE, help=f"Path to the ratings CSV file. Defaults to {DEFAULT_RATINGS_FILE}")
    update_parser.add_argument("--matches_file", type=pathlib.Path, default=DEFAULT_MATCHES_FILE, help=f"Path to the matches CSV file. Defaults to {DEFAULT_MATCHES_FILE}")

    run_parser = subparsers.add_parser("run", help="Run the full pipeline: collect -> extract -> update.")
    run_parser.add_argument("--date", type=str, required=True, help="The date for which the pipeline should run (affects collection stage).")

    args = parser.parse_args() # Full parse

    # Logging level is set by setup_logging using logging_args.verbose.
    # args.verbose (from the main parser) is available if needed for other logic,
    # but logging setup is complete.

    # Log global flags if they are set
    if args.verbose: # Explicitly log that verbose is on, if it was set
        logger.debug("Verbose mode enabled.", extra={'logging_level': 'DEBUG'})
    if args.dry_run:
        logger.info("Dry-run mode is active for this operation.", extra={'dry_run_global': True})

    # No need to log verbose mode explicitly here, as setup_logging handles the level.
    # If args.verbose is True, DEBUG logs will appear; otherwise, they won't.

    logger.debug("Pipeline arguments parsed", extra={'command': args.command, 'arguments': vars(args)})

    if args.command == "collect":
        handle_collect(args)
    elif args.command == "extract":
        handle_extract(args)
    elif args.command == "update":
        handle_update(args)
    elif args.command == "run":
        handle_run(args)
    else:
        logger.error("Unknown command", extra={'command': args.command})
        parser.print_help()

if __name__ == "__main__":
    main()
