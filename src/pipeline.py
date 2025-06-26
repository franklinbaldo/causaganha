import argparse
import logging
from pathlib import Path
import sys
import json
import shutil
import pandas as pd
import datetime

# Assuming downloader and extractor are stable and correct
from downloader import fetch_tjro_pdf as _real_fetch_tjro_pdf
from extractor import GeminiExtractor as _RealGeminiExtractor

# --- Configuration and OpenSkill Setup ---
try:
    from utils import normalize_lawyer_name, validate_decision
    from config import load_config

    CONFIG = load_config()

    from openskill_rating import (
        get_openskill_model,
        create_rating as create_openskill_rating_object,
        rate_teams as update_openskill_ratings,
        # OpenSkillRating # Type hint, not directly used for creation here
    )

    # Enum for match results (still useful internally)
    from enum import Enum

    class MatchResult(Enum):
        WIN_A = "win_a"
        WIN_B = "win_b"
        DRAW = "draw"
        PARTIAL_A = "partial_a"
        PARTIAL_B = "partial_b"

    RATING_ENGINE_NAME = "openskill"  # Hardcoded as it's the only engine now
    OS_CONFIG = CONFIG.get(
        "openskill", {}
    )  # Get OpenSkill specific config, or empty dict

    RATING_MODEL_INSTANCE = get_openskill_model(OS_CONFIG)
    DEFAULT_MU = OS_CONFIG.get("mu", 25.0)  # Fallback if not in OS_CONFIG
    DEFAULT_SIGMA = OS_CONFIG.get("sigma", 25.0 / 3.0)  # Fallback

    # Lambda functions for consistent interface
    def CREATE_RATING_FROM_MU_SIGMA_FUNC(mu, sigma):
        return create_openskill_rating_object(
            RATING_MODEL_INSTANCE, mu=float(mu), sigma=float(sigma)
        )

    def CREATE_NEW_RATING_FUNC():
        return create_openskill_rating_object(RATING_MODEL_INSTANCE)

    # OpenSkill's rate_teams expects the string value of the enum (e.g., "win_a")
    def UPDATE_RATINGS_FUNC(model, t_a, t_b, res_enum):
        return update_openskill_ratings(model, t_a, t_b, res_enum.value)

except ImportError as e:
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.CRITICAL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.critical(
        f"Failed to import critical modules (utils, config, openskill_rating): {e}. Pipeline cannot run."
    )
    sys.exit(1)


# --- Core Pipeline Functions (fetch_tjro_pdf, GeminiExtractor, setup_logging, command functions) ---
# These remain largely the same as before, except _update_ratings_logic and its callers.


def fetch_tjro_pdf(date_str: str, dry_run: bool = False, verbose: bool = False):
    logger = logging.getLogger(__name__)
    if dry_run:
        logger.info(f"DRY-RUN: Would fetch TJRO PDF for date: {date_str}")
        return Path(f"/tmp/fake_tjro_{date_str.replace('-', '')}.pdf")
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.warning(f"Invalid date '{date_str}', attempting direct pass")
        try:
            date_obj = datetime.date.fromisoformat(date_str)
        except ValueError:
            logger.error("Could not parse date '%s'", date_str)
            return None
    pdf_path = _real_fetch_tjro_pdf(date_obj)
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
        output_json_dir = (
            Path(output_json_dir)
            if output_json_dir
            else pdf_path.parent / "json_extracted"
        )
        output_json_dir.mkdir(parents=True, exist_ok=True)
        output_json_path = output_json_dir / f"{pdf_path.stem}_extracted.json"
        if dry_run:
            self.logger.info(
                f"DRY-RUN: Would extract from {pdf_path} to {output_json_path}"
            )
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"file_name_source": pdf_path.name, "simulated": True}, f, indent=2
                )
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
    logger.debug(f"Collect command: {args}")
    pdf_path = fetch_tjro_pdf(
        date_str=args.date, dry_run=args.dry_run, verbose=args.verbose
    )
    if pdf_path:
        logger.info(f"Collect successful. PDF: {pdf_path}")
    else:
        logger.error("Collect failed.")
    return pdf_path


def extract_command(args):
    logger = logging.getLogger(__name__)
    logger.debug(f"Extract command: {args}")
    output_dir = (
        Path(args.output_json_dir)
        if args.output_json_dir
        else Path(args.pdf_file).parent
    )
    extractor = GeminiExtractor(verbose=args.verbose)
    json_path = extractor.extract_and_save_json(
        pdf_path=Path(args.pdf_file), output_json_dir=output_dir, dry_run=args.dry_run
    )
    if json_path:
        logger.info(f"Extract successful. JSON: {json_path}")
    else:
        logger.error("Extract failed.")
    return json_path


def _update_ratings_logic(logger: logging.Logger, dry_run: bool):
    logger.info("Starting OpenSkill ratings update process.")  # Now always OpenSkill
    if dry_run:
        logger.info("DRY-RUN: OpenSkill update process simulation, no files changed.")

    json_input_dir = Path("causaganha/data/json/")
    processed_json_dir = Path("causaganha/data/json_processed/")
    ratings_file = Path("causaganha/data/ratings.csv")
    partidas_file = Path("causaganha/data/partidas.csv")

    try:
        ratings_df = pd.read_csv(ratings_file, index_col="advogado_id")
        if "mu" in ratings_df.columns:
            ratings_df["mu"] = ratings_df["mu"].astype(float)
        if "sigma" in ratings_df.columns:
            ratings_df["sigma"] = ratings_df["sigma"].astype(float)
        logger.info(f"Loaded ratings from {ratings_file}")
    except FileNotFoundError:
        logger.info(f"{ratings_file} not found. Initializing new ratings DataFrame.")
        ratings_df = pd.DataFrame(columns=["mu", "sigma", "total_partidas"]).set_index(
            pd.Index([], name="advogado_id")
        )
    except (pd.errors.EmptyDataError, ValueError) as e:
        logger.error(
            f"Error loading {ratings_file}: {e}. Initializing new ratings DataFrame."
        )
        ratings_df = pd.DataFrame(columns=["mu", "sigma", "total_partidas"]).set_index(
            pd.Index([], name="advogado_id")
        )

    for col in ["mu", "sigma", "total_partidas"]:
        if col not in ratings_df.columns:
            if col == "mu":
                ratings_df[col] = DEFAULT_MU
            elif col == "sigma":
                ratings_df[col] = DEFAULT_SIGMA
            else:
                ratings_df[col] = 0
    ratings_df["mu"] = ratings_df["mu"].astype(float)
    ratings_df["sigma"] = ratings_df["sigma"].astype(float)
    ratings_df["total_partidas"] = ratings_df["total_partidas"].astype(int)

    partidas_history = []
    processed_files_paths = []
    if not json_input_dir.exists():
        logger.error(f"JSON input directory not found: {json_input_dir}")
        return
    json_files_to_process = list(json_input_dir.glob("*.json"))
    if not json_files_to_process:
        logger.info(f"No JSON files in {json_input_dir} to process.")

    for json_path in json_files_to_process:
        logger.info(f"Processing JSON file: {json_path.name}")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                loaded_content = json.load(f)
        except Exception as e:
            logger.error(f"Error reading/decoding {json_path.name}: {e}. Skipping.")
            continue

        decisions_in_file = (
            loaded_content.get("decisions", [])
            if isinstance(loaded_content, dict)
            else loaded_content
            if isinstance(loaded_content, list)
            else [loaded_content]
            if loaded_content
            else []
        )

        file_had_valid_decisions = False
        for decision_data in decisions_in_file:
            if not validate_decision(decision_data):
                logger.warning(
                    f"Skipping invalid decision in {json_path.name} (processo: {decision_data.get('numero_processo', 'N/A')})."
                )
                continue

            raw_advs_polo_ativo = decision_data.get("advogados_polo_ativo", [])
            raw_advs_polo_passivo = decision_data.get("advogados_polo_passivo", [])
            team_a_ids = sorted(
                list(
                    set(
                        normalize_lawyer_name(name)
                        for name in raw_advs_polo_ativo
                        if normalize_lawyer_name(name)
                    )
                )
            )
            team_b_ids = sorted(
                list(
                    set(
                        normalize_lawyer_name(name)
                        for name in raw_advs_polo_passivo
                        if normalize_lawyer_name(name)
                    )
                )
            )

            if not team_a_ids or not team_b_ids:
                logger.warning(
                    f"Missing lawyers in {json_path.name} ({decision_data.get('numero_processo')}). Skipping."
                )
                continue
            if set(team_a_ids) == set(team_b_ids):
                logger.info(
                    f"Identical teams in {decision_data.get('numero_processo')}. Skipping."
                )
                continue

            resultado_str_raw = decision_data.get("resultado", "").lower()
            match_outcome = MatchResult.DRAW
            if resultado_str_raw in ["procedente", "provido", "confirmada"]:
                match_outcome = MatchResult.WIN_A
            elif resultado_str_raw in [
                "improcedente",
                "negado_provimento",
                "reformada",
            ]:
                match_outcome = MatchResult.WIN_B

            team_a_ratings_before = [
                CREATE_RATING_FROM_MU_SIGMA_FUNC(
                    ratings_df.loc[adv_id, "mu"], ratings_df.loc[adv_id, "sigma"]
                )
                if adv_id in ratings_df.index
                else CREATE_NEW_RATING_FUNC()
                for adv_id in team_a_ids
            ]
            team_b_ratings_before = [
                CREATE_RATING_FROM_MU_SIGMA_FUNC(
                    ratings_df.loc[adv_id, "mu"], ratings_df.loc[adv_id, "sigma"]
                )
                if adv_id in ratings_df.index
                else CREATE_NEW_RATING_FUNC()
                for adv_id in team_b_ids
            ]

            partida_team_a_ratings_before_dict = {
                adv_id: (r.mu, r.sigma)
                for adv_id, r in zip(team_a_ids, team_a_ratings_before)
            }
            partida_team_b_ratings_before_dict = {
                adv_id: (r.mu, r.sigma)
                for adv_id, r in zip(team_b_ids, team_b_ratings_before)
            }

            new_team_a_ratings, new_team_b_ratings = UPDATE_RATINGS_FUNC(
                RATING_MODEL_INSTANCE,
                team_a_ratings_before,
                team_b_ratings_before,
                match_outcome,
            )

            for i, adv_id in enumerate(team_a_ids):
                current_partidas = (
                    ratings_df.loc[adv_id, "total_partidas"]
                    if adv_id in ratings_df.index
                    else 0
                )
                ratings_df.loc[adv_id, ["mu", "sigma", "total_partidas"]] = [
                    new_team_a_ratings[i].mu,
                    new_team_a_ratings[i].sigma,
                    current_partidas + 1,
                ]
            for i, adv_id in enumerate(team_b_ids):
                current_partidas = (
                    ratings_df.loc[adv_id, "total_partidas"]
                    if adv_id in ratings_df.index
                    else 0
                )
                ratings_df.loc[adv_id, ["mu", "sigma", "total_partidas"]] = [
                    new_team_b_ratings[i].mu,
                    new_team_b_ratings[i].sigma,
                    current_partidas + 1,
                ]

            logger.debug(
                f"OpenSkill updated: A:{[f'{r.mu:.1f}±{r.sigma:.1f}' for r in new_team_a_ratings]} vs B:{[f'{r.mu:.1f}±{r.sigma:.1f}' for r in new_team_b_ratings]}"
            )
            partidas_history.append(
                {
                    "data_partida": decision_data.get(
                        "data_decisao", datetime.date.today().isoformat()
                    ),
                    "equipe_a_ids": ",".join(team_a_ids),
                    "equipe_b_ids": ",".join(team_b_ids),
                    "ratings_equipe_a_antes": json.dumps(
                        partida_team_a_ratings_before_dict
                    ),
                    "ratings_equipe_b_antes": json.dumps(
                        partida_team_b_ratings_before_dict
                    ),
                    "resultado_partida": match_outcome.value,
                    "ratings_equipe_a_depois": json.dumps(
                        {
                            adv_id: (r.mu, r.sigma)
                            for adv_id, r in zip(team_a_ids, new_team_a_ratings)
                        }
                    ),
                    "ratings_equipe_b_depois": json.dumps(
                        {
                            adv_id: (r.mu, r.sigma)
                            for adv_id, r in zip(team_b_ids, new_team_b_ratings)
                        }
                    ),
                    "numero_processo": decision_data.get("numero_processo"),
                }
            )
            file_had_valid_decisions = True
        if file_had_valid_decisions:
            processed_files_paths.append(json_path)

    if not dry_run:
        if not ratings_df.empty:
            try:
                if ratings_df.index.name is None:
                    ratings_df.index.name = "advogado_id"
                ratings_df.sort_values(
                    by=["mu", "sigma"], ascending=[False, True]
                ).to_csv(ratings_file)
                logger.info(f"Ratings saved to {ratings_file}")
            except Exception as e:
                logger.error(f"Error saving ratings to {ratings_file}: {e}")
        else:
            logger.info("Ratings DataFrame empty. Not saving.")
        if partidas_history:
            try:
                pd.DataFrame(partidas_history).to_csv(partidas_file, index=False)
                logger.info(f"Partidas history saved to {partidas_file}")
            except Exception as e:
                logger.error(f"Error saving partidas to {partidas_file}: {e}")
        else:
            logger.info("No new partidas to save.")
        if processed_files_paths:
            processed_json_dir.mkdir(parents=True, exist_ok=True)
            for p_file in processed_files_paths:
                try:
                    shutil.move(str(p_file), str(processed_json_dir / p_file.name))
                    logger.info(f"Moved {p_file.name} to {processed_json_dir}")
                except Exception as e:
                    logger.error(f"Error moving {p_file.name}: {e}")
        else:
            logger.info("No JSON files processed to move.")
    else:
        logger.info("DRY-RUN: Skipping save/move for OpenSkill.")
        if not ratings_df.empty:
            logger.info(f"DRY-RUN: Would save {len(ratings_df)} ratings.")
        if partidas_history:
            logger.info(f"DRY-RUN: Would save {len(partidas_history)} partidas.")
        if processed_files_paths:
            logger.info(f"DRY-RUN: Would move {len(processed_files_paths)} JSONs.")
    logger.info("OpenSkill ratings update process finished.")


def update_command(args):
    logger = logging.getLogger(__name__)
    logger.debug(f"Update command called with args: {args}")
    _update_ratings_logic(logger, args.dry_run)


def run_command(args):
    logger = logging.getLogger(__name__)
    logger.debug(f"Run command called with args: {args}")
    logger.info(f"Starting 'collect' step for date {args.date}...")
    pdf_path = fetch_tjro_pdf(
        date_str=args.date, dry_run=args.dry_run, verbose=args.verbose
    )
    if not pdf_path:
        logger.error(f"'collect' failed for {args.date}. Aborting.")
        return
    logger.info(f"'collect' successful. PDF: {pdf_path}")
    logger.info(f"Starting 'extract' for PDF {pdf_path}...")
    extract_output_dir = (
        Path(args.output_json_dir)
        if args.output_json_dir
        else Path("causaganha/data/json/")
    )
    extractor = GeminiExtractor(verbose=args.verbose)
    json_output_path = extractor.extract_and_save_json(
        pdf_path=pdf_path, output_json_dir=extract_output_dir, dry_run=args.dry_run
    )
    if not json_output_path:
        logger.error(f"'extract' failed for {pdf_path}. 'run' partially completed.")
        return
    logger.info(f"'extract' successful. JSON: {json_output_path}")
    logger.info("Starting 'update' as part of 'run'...")
    update_args = argparse.Namespace(dry_run=args.dry_run, verbose=args.verbose)
    update_command(update_args)
    logger.info(f"Run command completed for {args.date}.")


def archive_command(args):
    logger = logging.getLogger(__name__)
    logger.debug(f"Archive command: {args}")
    if args.dry_run:
        logger.info(
            f"DRY-RUN: Archive: type={args.archive_type}, date={args.date or 'today'}, db={args.db_path}"
        )
        return
    try:
        from archive_db import DatabaseArchiver, IAConfig
        from datetime import datetime, date as DateObject

        snap_date = (
            datetime.strptime(args.date, "%Y-%m-%d").date()
            if args.date
            else DateObject.today()
        )
        logger.info(
            f"Starting archive: type={args.archive_type}, date={snap_date}, db={args.db_path}"
        )
        if not args.db_path.exists():
            logger.error(f"DB not found: {args.db_path}")
            return
        archiver = DatabaseArchiver(IAConfig.from_env())
        if archiver.archive_database(
            db_path=args.db_path,
            snapshot_date=snap_date,
            archive_type=args.archive_type,
        ):
            logger.info("✅ Database archive completed successfully")
        else:
            logger.error("❌ Database archive failed")
    except ImportError as e:
        logger.error(f"Archive import error: {e}. 'internetarchive' installed?")
    except ValueError as e:
        logger.error(f"Archive config error: {e}. Check IA env vars.")
    except Exception as e:
        logger.error(f"Archive command failed: {e}", exc_info=args.verbose)


def main():
    parser = argparse.ArgumentParser(
        description="CausaGanha Legal Rating ETL Pipeline."
    )
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logging.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Commands")

    # Simplified argument definitions
    cmd_definitions = [
        (
            "collect",
            "Downloads documents.",
            collect_command,
            [
                ("--date", {"required": True, "help": "Date (YYYY-MM-DD)."}),
                ("--dry-run", {"action": "store_true"}),
            ],
        ),
        (
            "extract",
            "Extracts PDF to JSON.",
            extract_command,
            [
                ("--pdf_file", {"required": True, "type": Path, "help": "PDF path."}),
                ("--output_json_dir", {"type": Path}),
                ("--dry-run", {"action": "store_true"}),
            ],
        ),
        (
            "update",
            "Updates ratings from JSONs.",
            update_command,
            [("--dry-run", {"action": "store_true"})],
        ),
        (
            "archive",
            "Archives database.",
            archive_command,
            [
                ("--date", {"help": "Snapshot date (YYYY-MM-DD, default: today)."}),
                (
                    "--archive-type",
                    {
                        "choices": ["weekly", "monthly", "quarterly"],
                        "default": "weekly",
                    },
                ),
                (
                    "--db-path",
                    {"type": Path, "default": Path("data/causaganha.duckdb")},
                ),
                ("--dry-run", {"action": "store_true"}),
            ],
        ),
        (
            "run",
            "Full pipeline: collect, extract, update.",
            run_command,
            [
                ("--date", {"required": True, "help": "Date (YYYY-MM-DD)."}),
                (
                    "--output_json_dir",
                    {"type": Path, "help": "JSON out dir for extract."},
                ),
                ("--dry-run", {"action": "store_true"}),
            ],
        ),
    ]

    for name, help_text, func, arg_list in cmd_definitions:
        p = subparsers.add_parser(name, help=help_text)
        p.set_defaults(func=func)
        for arg_name, arg_params in arg_list:
            p.add_argument(arg_name, **arg_params)

    args = parser.parse_args()
    setup_logging(args.verbose if hasattr(args, "verbose") else False)

    logger = logging.getLogger(__name__)
    logger.debug(f"Command: {args.command}, Args: {vars(args)}")
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
