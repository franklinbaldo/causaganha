import argparse
import logging
from pathlib import Path
import sys
import json
import shutil
import pandas as pd
import datetime

from .downloader import fetch_tjro_pdf as _real_fetch_tjro_pdf
from .extractor import GeminiExtractor as _RealGeminiExtractor

# Attempt to import local modules
try:
    from .utils import normalize_lawyer_name, validate_decision
    from .elo import (
        update_elo,
    )  # Assuming expected_score is not directly needed by pipeline logic
except ImportError as e:
    # This might happen if script is run directly and not as part of the package.
    # For robustness in such scenarios, or if structure changes, direct import might be an alternative.
    # from utils import normalize_lawyer_name, validate_decision # etc.
    logging.error(
        f"Failed to import local modules (.utils, .elo): {e}. Ensure they are in the correct path."
    )

    # Define dummy functions if imports fail, to allow basic CLI to load, but update will fail.
    def normalize_lawyer_name(name):
        return name

    def validate_decision(decision):
        return False

    def update_elo(r1, r2, s1, k):
        return r1, r2


# Constants for Elo update
DEFAULT_RATING = 1500.0
K_FACTOR = 16  # Standard K-factor


# Wrappers around the real downloader/extractor to keep the CLI tests stable
def fetch_tjro_pdf(date_str: str, dry_run: bool = False, verbose: bool = False):
    logger = logging.getLogger(__name__)
    if dry_run:
        logger.info(f"DRY-RUN: Would fetch TJRO PDF for date: {date_str}")
        return Path(f"/tmp/fake_tjro_{date_str.replace('-', '')}.pdf")

    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.warning(
            f"Invalid date '{date_str}' passed to fetch_tjro_pdf; attempting direct pass"
        )
        try:
            date_obj = datetime.date.fromisoformat(date_str)
        except ValueError:
            logger.error(f"Could not parse date '{date_str}'")
            return None

    pdf_path = _real_fetch_tjro_pdf(date_obj)
    if pdf_path:
        try:
            from .gdrive import upload_file_to_gdrive

            upload_file_to_gdrive(pdf_path)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to upload {pdf_path} to GDrive: {e}")
    return pdf_path


class GeminiExtractor:
    def __init__(self, verbose: bool = False):
        self.logger = logging.getLogger(__name__)
        self.verbose = verbose
        self._real = _RealGeminiExtractor()

    def extract_and_save_json(
        self, pdf_path: Path, output_json_dir: Path = None, dry_run: bool = False
    ):
        self.logger.debug(f"Attempting to extract text from PDF: {pdf_path}")

        if output_json_dir is None:
            output_json_dir = pdf_path.parent / "json_extracted"
        else:
            output_json_dir = Path(output_json_dir)

        output_json_dir.mkdir(parents=True, exist_ok=True)
        output_json_path = output_json_dir / f"{pdf_path.stem}_extracted.json"

        if dry_run:
            self.logger.info(
                f"DRY-RUN: Would extract text from {pdf_path} and save to {output_json_path}"
            )
            dummy_content = {
                "file_name_source": pdf_path.name,
                "extracted_data_simulated": True,
            }
            with open(output_json_path, "w") as f:
                json.dump(dummy_content, f, indent=2)
            return output_json_path

        return self._real.extract_and_save_json(pdf_path, output_json_dir)


def setup_logging(verbose: bool):
    log_level = logging.DEBUG if verbose else logging.INFO
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        stream=sys.stdout,
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def collect_command(args):
    logger = logging.getLogger(__name__)
    logger.debug(f"Collect command called with args: {args}")
    pdf_path = fetch_tjro_pdf(
        date_str=args.date, dry_run=args.dry_run, verbose=args.verbose
    )
    if pdf_path:
        logger.info(f"Collect command successful. PDF path: {pdf_path}")
        return pdf_path
    else:
        logger.error("Collect command failed.")
        return None


def extract_command(args):
    logger = logging.getLogger(__name__)
    logger.debug(f"Extract command called with args: {args}")
    pdf_file_path = Path(args.pdf_file)
    # If output_json_dir is not specified for extract, it defaults to the PDF's directory.
    # This is different from the GeminiExtractor's internal default if output_json_dir is None.
    output_dir = (
        Path(args.output_json_dir) if args.output_json_dir else pdf_file_path.parent
    )

    extractor = GeminiExtractor(verbose=args.verbose)
    json_path = extractor.extract_and_save_json(
        pdf_path=pdf_file_path, output_json_dir=output_dir, dry_run=args.dry_run
    )
    if json_path:
        logger.info(f"Extract command successful. JSON path: {json_path}")
        return json_path
    else:
        logger.error("Extract command failed.")
        return None


# Renamed from _handle_update_logic to fit into the command structure
def _update_elo_ratings_logic(logger: logging.Logger, dry_run: bool):
    logger.info("Starting Elo update process.")
    if dry_run:
        logger.info("DRY-RUN: Elo update process would run, no files will be changed.")

    json_input_dir = Path("causaganha/data/json/")
    processed_json_dir = Path("causaganha/data/json_processed/")
    ratings_file = Path("causaganha/data/ratings.csv")
    partidas_file = Path("causaganha/data/partidas.csv")

    # Load Ratings
    try:
        ratings_df = pd.read_csv(ratings_file, index_col="advogado_id")
        logger.info(f"Loaded ratings from {ratings_file}")
    except FileNotFoundError:
        logger.info(f"{ratings_file} not found. Initializing new ratings DataFrame.")
        ratings_df = pd.DataFrame(columns=["rating", "total_partidas"]).set_index(
            pd.Index([], name="advogado_id")
        )
    except Exception as e:
        logger.error(
            f"Error loading {ratings_file}: {e}. Initializing new ratings DataFrame."
        )
        ratings_df = pd.DataFrame(columns=["rating", "total_partidas"]).set_index(
            pd.Index([], name="advogado_id")
        )

    if dry_run:
        # For dry run, we operate on a copy so changes aren't persisted if we were to save.
        # However, the save operations are skipped anyway in dry_run.
        pass

    partidas_history = []
    processed_files_paths = []  # Keep track of files processed in this run

    if not json_input_dir.exists():
        logger.error(f"JSON input directory not found: {json_input_dir}")
        return

    json_files_to_process = list(json_input_dir.glob("*.json"))
    if not json_files_to_process:
        logger.info(f"No JSON files found in {json_input_dir} to process.")
        # Still save ratings/partidas if they exist from previous runs and need sorting/creation

    for json_path in json_files_to_process:
        logger.info(f"Processing JSON file: {json_path.name}")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                loaded_content = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(
                f"Error decoding JSON from {json_path.name}: {e}. Skipping file."
            )
            continue
        except Exception as e:
            logger.error(f"Error reading {json_path.name}: {e}. Skipping file.")
            continue

        decisions_in_file = (
            loaded_content if isinstance(loaded_content, list) else [loaded_content]
        )

        file_had_valid_decisions_for_elo = False
        for decision_data in decisions_in_file:
            if not validate_decision(decision_data):  # validate_decision logs reasons
                logger.warning(
                    f"Skipping invalid decision in {json_path.name} (processo: {decision_data.get('numero_processo', 'N/A')})."
                )
                continue

            advogados_data = decision_data.get("advogados", {})
            advogados_requerente = advogados_data.get("requerente", [])
            advogados_requerido = advogados_data.get("requerido", [])

            if not advogados_requerente or not advogados_requerido:
                logger.warning(
                    f"Missing lawyers for one or both parties in {json_path.name} (processo: {decision_data.get('numero_processo')}). Skipping decision."
                )
                continue

            # Taking the first lawyer from each list for the Elo match
            adv_a_raw_id = advogados_requerente[0]
            adv_b_raw_id = advogados_requerido[0]

            adv_a_id = normalize_lawyer_name(adv_a_raw_id)
            adv_b_id = normalize_lawyer_name(adv_b_raw_id)

            if (
                not adv_a_id or not adv_b_id
            ):  # Handle cases where normalization might return empty
                logger.warning(
                    f"Could not normalize one or both lawyer IDs ('{adv_a_raw_id}', '{adv_b_raw_id}') for {decision_data.get('numero_processo')}. Skipping."
                )
                continue

            if adv_a_id == adv_b_id:
                logger.info(
                    f"Same lawyer ('{adv_a_id}') for both parties in {decision_data.get('numero_processo')}. Skipping Elo update for this pair."
                )
                continue

            resultado_str = decision_data.get("resultado", "").lower()
            score_a = 0.5  # Default to draw for unknown outcomes
            if resultado_str == "procedente":
                score_a = 1.0
            elif resultado_str == "improcedente":
                score_a = 0.0
            elif resultado_str in [
                "parcialmente procedente",
                "parcialmente_procedente",
                "extinto sem resolução de mérito",
                "extinto",
            ]:
                score_a = 0.5
            else:
                logger.warning(
                    f"Unknown 'resultado' ('{resultado_str}') for {decision_data.get('numero_processo')}. Treating as a draw (0.5)."
                )

            rating_a = (
                ratings_df.loc[adv_a_id, "rating"]
                if adv_a_id in ratings_df.index
                else DEFAULT_RATING
            )
            rating_b = (
                ratings_df.loc[adv_b_id, "rating"]
                if adv_b_id in ratings_df.index
                else DEFAULT_RATING
            )

            rating_a_antes = rating_a
            rating_b_antes = rating_b

            new_rating_a, new_rating_b = update_elo(
                rating_a, rating_b, score_a, k_factor=K_FACTOR
            )

            # Update ratings_df for adv_a_id
            current_partidas_a = (
                ratings_df.loc[adv_a_id, "total_partidas"]
                if adv_a_id in ratings_df.index
                else 0
            )
            ratings_df.loc[adv_a_id, ["rating", "total_partidas"]] = [
                new_rating_a,
                current_partidas_a + 1,
            ]

            # Update ratings_df for adv_b_id
            current_partidas_b = (
                ratings_df.loc[adv_b_id, "total_partidas"]
                if adv_b_id in ratings_df.index
                else 0
            )
            ratings_df.loc[adv_b_id, ["rating", "total_partidas"]] = [
                new_rating_b,
                current_partidas_b + 1,
            ]

            logger.debug(
                f"Elo updated for {adv_a_id} ({rating_a_antes:.1f} -> {new_rating_a:.1f}) vs {adv_b_id} ({rating_b_antes:.1f} -> {new_rating_b:.1f})"
            )

            partidas_history.append(
                {
                    "data_partida": decision_data.get(
                        "data_decisao", datetime.date.today().isoformat()
                    ),
                    "advogado_a_id": adv_a_id,
                    "advogado_b_id": adv_b_id,
                    "rating_advogado_a_antes": rating_a_antes,
                    "rating_advogado_b_antes": rating_b_antes,
                    "score_a": score_a,
                    "rating_advogado_a_depois": new_rating_a,
                    "rating_advogado_b_depois": new_rating_b,
                    "numero_processo": decision_data.get("numero_processo"),
                }
            )
            file_had_valid_decisions_for_elo = True

        if file_had_valid_decisions_for_elo:
            processed_files_paths.append(json_path)

    if not dry_run:
        if not ratings_df.empty:
            try:
                # Ensure index has a name for pd.to_csv
                if ratings_df.index.name is None:
                    ratings_df.index.name = "advogado_id"
                ratings_df_sorted = ratings_df.sort_values(by="rating", ascending=False)
                ratings_df_sorted.to_csv(ratings_file)
                logger.info(f"Ratings saved to {ratings_file}")
            except Exception as e:
                logger.error(f"Error saving ratings to {ratings_file}: {e}")
        else:
            logger.info("Ratings DataFrame is empty. Not saving ratings file.")

        if partidas_history:
            partidas_df = pd.DataFrame(partidas_history)
            try:
                partidas_df.to_csv(partidas_file, index=False)
                logger.info(f"Partidas history saved to {partidas_file}")
            except Exception as e:
                logger.error(f"Error saving partidas to {partidas_file}: {e}")
        else:
            logger.info("No new partidas to save.")

        if processed_files_paths:
            processed_json_dir.mkdir(parents=True, exist_ok=True)
            for processed_file_path in processed_files_paths:
                try:
                    destination = processed_json_dir / processed_file_path.name
                    shutil.move(str(processed_file_path), str(destination))
                    logger.info(
                        f"Moved processed JSON file {processed_file_path.name} to {destination}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error moving file {processed_file_path.name} to {processed_json_dir}: {e}"
                    )
        else:
            logger.info("No JSON files were successfully processed to be moved.")

    else:  # Dry run
        logger.info(
            "DRY-RUN: Skipping save of ratings, partidas, and move of JSON files."
        )
        if not ratings_df.empty:
            logger.info(f"DRY-RUN: Would attempt to save {len(ratings_df)} ratings.")
        if partidas_history:
            logger.info(
                f"DRY-RUN: Would attempt to save {len(partidas_history)} partidas."
            )
        if processed_files_paths:
            logger.info(
                f"DRY-RUN: Would attempt to move {len(processed_files_paths)} JSON files."
            )

    logger.info("Elo update process finished.")


def update_command(args):
    logger = logging.getLogger(__name__)
    logger.debug(f"Update command called with args: {args}")

    # The main logic is now encapsulated in _update_elo_ratings_logic
    _update_elo_ratings_logic(logger, args.dry_run)


def run_command(args):
    logger = logging.getLogger(__name__)
    logger.debug(f"Run command called with args: {args}")

    logger.info(f"Starting 'collect' step for date {args.date}...")
    pdf_path = fetch_tjro_pdf(
        date_str=args.date, dry_run=args.dry_run, verbose=args.verbose
    )
    if not pdf_path:
        logger.error(f"'collect' step failed for date {args.date}. Aborting 'run'.")
        return
    logger.info(f"'collect' step successful. PDF available at: {pdf_path}")

    logger.info(f"Starting 'extract' step for PDF {pdf_path}...")
    # For 'run', if --output_json_dir is given to 'run', it's for the final JSON output of the pipeline.
    # The extract step here should probably save to the default location for 'update' to find it.
    # So, `causaganha/data/json/` is the target for extract step in a `run` command.
    # The GeminiExtractor's default is relative to the PDF, which might be /tmp/.
    # Let's make it explicit for the run command.
    extract_output_dir = (
        Path(args.output_json_dir)
        if args.output_json_dir
        else Path("causaganha/data/json/")
    )

    extractor = GeminiExtractor(verbose=args.verbose)
    json_output_path = extractor.extract_and_save_json(
        pdf_path=pdf_path,
        output_json_dir=extract_output_dir,  # Explicitly pass where extracted JSONs should go
        dry_run=args.dry_run,
    )
    if not json_output_path:
        logger.error(
            f"'extract' step failed for PDF {pdf_path}. 'run' command partially completed."
        )
        return
    logger.info(f"'extract' step successful. JSON output at: {json_output_path}")

    # --- Update Step (as part of run) ---
    logger.info("Starting 'update' step as part of 'run' command...")
    # Create a simple Namespace for args to pass to update_command's logic
    # The update logic doesn't depend on many args, mainly dry_run and verbose (which is global)
    update_args = argparse.Namespace(dry_run=args.dry_run, verbose=args.verbose)
    update_command(update_args)  # Call the update_command function

    logger.info(f"Run command completed successfully for date {args.date}.")


def main():
    parser = argparse.ArgumentParser(description="CausaGanha LegalELo ETL Pipeline.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed logging (DEBUG level) for all operations.",
    )

    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available commands."
    )

    collect_parser = subparsers.add_parser(
        "collect", help="Downloads official legal documents for a specific date."
    )
    collect_parser.add_argument(
        "--date",
        required=True,
        help="Date in YYYY-MM-DD format to collect documents for.",
    )
    collect_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate data collection without downloading.",
    )
    collect_parser.set_defaults(func=collect_command)

    extract_parser = subparsers.add_parser(
        "extract", help="Extracts information from a PDF document to JSON."
    )
    extract_parser.add_argument(
        "--pdf_file", required=True, type=Path, help="Path to the PDF file to process."
    )
    extract_parser.add_argument(
        "--output_json_dir",
        type=Path,
        help="Optional directory to save the output JSON file. Defaults to PDF's directory.",
    )
    extract_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate extraction without processing or saving.",
    )
    extract_parser.set_defaults(func=extract_command)

    update_parser = subparsers.add_parser(
        "update",
        help="Updates Elo ratings and match history from processed JSON files.",
    )
    update_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate update without changing ratings/partidas files or moving JSONs.",
    )
    update_parser.set_defaults(func=update_command)

    run_parser = subparsers.add_parser(
        "run",
        help="Runs the full collect, extract, and update pipeline for a specific date.",
    )
    run_parser.add_argument(
        "--date", required=True, help="Date in YYYY-MM-DD format for the pipeline."
    )
    # output_json_dir for 'run' could specify where the 'extract' step places its files.
    # If not specified, extract might use its default (e.g. data/json or relative to PDF).
    # For 'run', it's important that 'extract' output goes where 'update' expects it.
    run_parser.add_argument(
        "--output_json_dir",
        type=Path,
        help="Optional: Directory for 'extract' to save JSONs. Defaults to 'causaganha/data/json/'.",
    )
    run_parser.add_argument(
        "--dry-run", action="store_true", help="Simulate the full pipeline run."
    )
    run_parser.set_defaults(func=run_command)

    args = parser.parse_args()

    global_verbose = args.verbose if hasattr(args, "verbose") else False
    setup_logging(global_verbose)

    if hasattr(args, "func"):
        args.verbose = global_verbose

    logger = logging.getLogger(__name__)
    logger.debug(
        f"Global verbose: {global_verbose}. Effective args for command: {args}"
    )

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
