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
    from .trueskill_rating import (
        ENV as TRUESKILL_ENV,  # Renomeado para evitar conflito com ENV de configuração do pipeline
        MatchResult,
        create_new_rating,
        update_ratings as update_trueskill_ratings,
        trueskill,  # To create Rating objects from stored mu/sigma
        TS_CONFIG,  # Acessar a configuração carregada do toml
    )
except ImportError as e:
    # This might happen if script is run directly and not as part of the package.
    logging.error(
        f"Failed to import local modules (.utils, .trueskill_rating): {e}. Ensure they are in the correct path."
    )

    # Define dummy functions if imports fail
    def normalize_lawyer_name(name):
        return name

    def validate_decision(decision):
        return False

    # Dummy TrueSkill related functions if import fails
    class DummyRating:
        def __init__(self, mu=25.0, sigma=8.33):
            self.mu = mu
            self.sigma = sigma

    def create_new_rating():
        return DummyRating()

    def update_trueskill_ratings(env, team_a, team_b, result):  # Added env for dummy
        # Return the same ratings passed in, to avoid breaking logic further down
        return team_a, team_b

    class DummyEnv:
        mu = 25.0
        sigma = 25.0 / 3.0

    TRUESKILL_ENV = DummyEnv()
    TS_CONFIG = {"mu": 25.0, "sigma": 25.0/3.0} # Dummy TS_CONFIG
    trueskill = None # So isinstance(rating, trueskill.Rating) would fail or be handled


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
# Now updates TrueSkill ratings instead of Elo
def _update_trueskill_ratings_logic(logger: logging.Logger, dry_run: bool):
    logger.info("Starting TrueSkill ratings update process.")
    if dry_run:
        logger.info("DRY-RUN: TrueSkill update process would run, no files will be changed.")

    json_input_dir = Path("causaganha/data/json/")
    processed_json_dir = Path("causaganha/data/json_processed/")
    ratings_file = Path("causaganha/data/ratings.csv")
    partidas_file = Path("causaganha/data/partidas.csv")

    # Load Ratings
    try:
        ratings_df = pd.read_csv(ratings_file, index_col="advogado_id")
        # Ensure correct dtypes for mu and sigma if they exist
        if "mu" in ratings_df.columns:
            ratings_df["mu"] = ratings_df["mu"].astype(float)
        if "sigma" in ratings_df.columns:
            ratings_df["sigma"] = ratings_df["sigma"].astype(float)
        logger.info(f"Loaded ratings from {ratings_file}")
    except FileNotFoundError:
        logger.info(f"{ratings_file} not found. Initializing new ratings DataFrame.")
        ratings_df = pd.DataFrame(
            columns=["mu", "sigma", "total_partidas"]
        ).set_index(pd.Index([], name="advogado_id"))
    except Exception as e:
        logger.error(
            f"Error loading {ratings_file}: {e}. Initializing new ratings DataFrame."
        )
        ratings_df = pd.DataFrame(
            columns=["mu", "sigma", "total_partidas"]
        ).set_index(pd.Index([], name="advogado_id"))

    # Ensure required columns exist for new DataFrames or after loading old format
    for col in ["mu", "sigma", "total_partidas"]:
        if col not in ratings_df.columns:
            if col == "mu":
                ratings_df[col] = TS_CONFIG.get("mu", 25.0)
            elif col == "sigma":
                ratings_df[col] = TS_CONFIG.get("sigma", 25.0/3.0)
            else: # total_partidas
                ratings_df[col] = 0

    ratings_df["mu"] = ratings_df["mu"].astype(float)
    ratings_df["sigma"] = ratings_df["sigma"].astype(float)
    ratings_df["total_partidas"] = ratings_df["total_partidas"].astype(int)


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

        if isinstance(loaded_content, dict) and "decisions" in loaded_content:
            decisions_in_file = loaded_content["decisions"]
        elif isinstance(loaded_content, list):
            decisions_in_file = loaded_content
        else:
            decisions_in_file = [loaded_content]

        file_had_valid_decisions = False
        for decision_data in decisions_in_file:
            if not validate_decision(decision_data):
                logger.warning(
                    f"Skipping invalid decision in {json_path.name} (processo: {decision_data.get('numero_processo', 'N/A')})."
                )
                continue

            raw_advs_polo_ativo = decision_data.get("advogados_polo_ativo", [])
            raw_advs_polo_passivo = decision_data.get("advogados_polo_passivo", [])

            # Normalize and filter lawyer names for Team A
            team_a_ids = sorted(list(set(
                normalize_lawyer_name(name) for name in raw_advs_polo_ativo if normalize_lawyer_name(name)
            )))
            # Normalize and filter lawyer names for Team B
            team_b_ids = sorted(list(set(
                normalize_lawyer_name(name) for name in raw_advs_polo_passivo if normalize_lawyer_name(name)
            )))

            if not team_a_ids or not team_b_ids:
                logger.warning(
                    f"Missing or empty normalized lawyer lists for one or both parties in {json_path.name} (processo: {decision_data.get('numero_processo')}). Skipping decision."
                )
                continue

            # Check if teams are identical after normalization
            if set(team_a_ids) == set(team_b_ids):
                logger.info(
                    f"Identical teams after normalization for {decision_data.get('numero_processo')} (Team A: {team_a_ids}, Team B: {team_b_ids}). Skipping."
                )
                continue

            resultado_str_raw = decision_data.get("resultado", "").lower()
            trueskill_match_result = MatchResult.DRAW
            if resultado_str_raw in ["procedente", "provido", "confirmada"]:
                trueskill_match_result = MatchResult.WIN_A
            elif resultado_str_raw in ["improcedente", "negado_provimento", "reformada"]:
                trueskill_match_result = MatchResult.WIN_B
            elif resultado_str_raw in [
                "parcialmente procedente", "parcialmente_procedente",
                "extinto sem resolução de mérito", "extinto", "não_definido",
            ]:
                trueskill_match_result = MatchResult.DRAW
            else:
                logger.warning(
                    f"Unknown 'resultado' ('{resultado_str_raw}') for {decision_data.get('numero_processo')}. Treating as a draw."
                )

            # Get ratings for Team A
            team_a_ratings_before = []
            for adv_id in team_a_ids:
                if adv_id in ratings_df.index:
                    mu = ratings_df.loc[adv_id, "mu"]
                    sigma = ratings_df.loc[adv_id, "sigma"]
                    team_a_ratings_before.append(trueskill.Rating(mu=mu, sigma=sigma))
                else:
                    team_a_ratings_before.append(create_new_rating())

            # Get ratings for Team B
            team_b_ratings_before = []
            for adv_id in team_b_ids:
                if adv_id in ratings_df.index:
                    mu = ratings_df.loc[adv_id, "mu"]
                    sigma = ratings_df.loc[adv_id, "sigma"]
                    team_b_ratings_before.append(trueskill.Rating(mu=mu, sigma=sigma))
                else:
                    team_b_ratings_before.append(create_new_rating())

            # Store ratings before update for history
            partida_team_a_ratings_before_dict = {
                adv_id: (r.mu, r.sigma) for adv_id, r in zip(team_a_ids, team_a_ratings_before)
            }
            partida_team_b_ratings_before_dict = {
                adv_id: (r.mu, r.sigma) for adv_id, r in zip(team_b_ids, team_b_ratings_before)
            }

            new_team_a_ratings, new_team_b_ratings = update_trueskill_ratings(
                TRUESKILL_ENV,
                team_a_ratings_before,
                team_b_ratings_before,
                trueskill_match_result,
            )

            # Update ratings_df for Team A
            for i, adv_id in enumerate(team_a_ids):
                current_partidas = ratings_df.loc[adv_id, "total_partidas"] if adv_id in ratings_df.index else 0
                ratings_df.loc[adv_id, ["mu", "sigma", "total_partidas"]] = [
                    new_team_a_ratings[i].mu,
                    new_team_a_ratings[i].sigma,
                    current_partidas + 1,
                ]

            # Update ratings_df for Team B
            for i, adv_id in enumerate(team_b_ids):
                current_partidas = ratings_df.loc[adv_id, "total_partidas"] if adv_id in ratings_df.index else 0
                ratings_df.loc[adv_id, ["mu", "sigma", "total_partidas"]] = [
                    new_team_b_ratings[i].mu,
                    new_team_b_ratings[i].sigma,
                    current_partidas + 1,
                ]

            logger.debug(
                f"TrueSkill updated for Team A ({[f'{r.mu:.1f}±{r.sigma:.1f}' for r in new_team_a_ratings]}) vs Team B ({[f'{r.mu:.1f}±{r.sigma:.1f}' for r in new_team_b_ratings]})"
            )

            # Store ratings after update for history
            partida_team_a_ratings_after_dict = {
                adv_id: (r.mu, r.sigma) for adv_id, r in zip(team_a_ids, new_team_a_ratings)
            }
            partida_team_b_ratings_after_dict = {
                adv_id: (r.mu, r.sigma) for adv_id, r in zip(team_b_ids, new_team_b_ratings)
            }

            partidas_history.append({
                "data_partida": decision_data.get("data_decisao", decision_data.get("data", datetime.date.today().isoformat())),
                "equipe_a_ids": ",".join(team_a_ids),
                "equipe_b_ids": ",".join(team_b_ids),
                "ratings_equipe_a_antes": json.dumps(partida_team_a_ratings_before_dict),
                "ratings_equipe_b_antes": json.dumps(partida_team_b_ratings_before_dict),
                "resultado_partida": trueskill_match_result.value,
                "ratings_equipe_a_depois": json.dumps(partida_team_a_ratings_after_dict),
                "ratings_equipe_b_depois": json.dumps(partida_team_b_ratings_after_dict),
                "numero_processo": decision_data.get("numero_processo"),
            })
            file_had_valid_decisions = True

        if file_had_valid_decisions:
            processed_files_paths.append(json_path)

    if not dry_run:
        if not ratings_df.empty:
            try:
                if ratings_df.index.name is None:
                    ratings_df.index.name = "advogado_id"
                # Sort by mu (primary rating) then sigma (uncertainty, lower is better for same mu)
                ratings_df_sorted = ratings_df.sort_values(by=["mu", "sigma"], ascending=[False, True])
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

    logger.info("TrueSkill ratings update process finished.")


def update_command(args):
    logger = logging.getLogger(__name__)
    logger.debug(f"Update command called with args: {args}")

    # The main logic is now encapsulated in _update_trueskill_ratings_logic
    _update_trueskill_ratings_logic(logger, args.dry_run)


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
