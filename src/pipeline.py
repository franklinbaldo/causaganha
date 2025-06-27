import argparse
import logging
from pathlib import Path
import sys
import json

# import pandas as pd # No longer directly needed for CSVs here
import datetime

# Corrected imports to be absolute from src
from src.tribunais.tjro.downloader import (
    fetch_tjro_pdf as _real_fetch_tjro_pdf,
)  # Corrected
from src.extractor import GeminiExtractor as _RealGeminiExtractor

# --- Import Database and PII Manager ---
from src.database import CausaGanhaDB
from src.pii_manager import PiiManager


# --- Configuration and OpenSkill Setup ---
try:
    # Standardize imports to be absolute from src
    from src.utils import normalize_lawyer_name, validate_decision
    from src.config import load_config

    CONFIG = load_config()

    from src.openskill_rating import (  # Standardize import
        get_openskill_model,
        create_rating as create_openskill_rating_object,
        rate_teams as update_openskill_ratings,
    )

    from enum import Enum

    class MatchResult(Enum):
        WIN_A = "win_a"
        WIN_B = "win_b"
        DRAW = "draw"
        PARTIAL_A = "partial_a"  # Not currently used in outcome logic but defined
        PARTIAL_B = "partial_b"  # Not currently used

    RATING_ENGINE_NAME = "openskill"
    OS_CONFIG = CONFIG.get("openskill", {})
    RATING_MODEL_INSTANCE = get_openskill_model(OS_CONFIG)
    DEFAULT_MU = OS_CONFIG.get("mu", 25.0)
    DEFAULT_SIGMA = OS_CONFIG.get("sigma", 25.0 / 3.0)

    def CREATE_RATING_FROM_MU_SIGMA_FUNC(mu, sigma):
        return create_openskill_rating_object(
            RATING_MODEL_INSTANCE, mu=float(mu), sigma=float(sigma)
        )

    def CREATE_NEW_RATING_FUNC():
        return create_openskill_rating_object(RATING_MODEL_INSTANCE)

    def UPDATE_RATINGS_FUNC(model, t_a, t_b, res_enum):
        return update_openskill_ratings(model, t_a, t_b, res_enum.value)

except ImportError as e:
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.CRITICAL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # Log the actual import error to help diagnose
    logging.critical(
        f"Failed to import critical modules. Original error: {e}. Pipeline cannot run."
    )
    sys.exit(1)


def fetch_tjro_pdf(date_str: str, dry_run: bool = False, verbose: bool = False):
    logger = logging.getLogger(__name__)
    if dry_run:
        logger.info(f"DRY-RUN: Would fetch TJRO PDF for date: {date_str}")
        # In dry run, we might not have a real PDF path, so return a placeholder
        return Path(f"/tmp/fake_tjro_{date_str.replace('-', '')}.pdf")

    # _real_fetch_tjro_pdf is imported from src.tribunais.tjro.downloader
    # Its signature in downloader.py is fetch_tjro_pdf(target_date: date, output_dir: Path = ...)
    # This wrapper needs to adapt. The original call in AGENTS.md was `causaganha pipeline run --date YYYY-MM-DD`
    # and in this file, it was `_real_fetch_tjro_pdf(date_obj)`
    # Let's assume _real_fetch_tjro_pdf from the actual downloader.py can take a date string or needs a date object.
    # The one in src.downloader (which was moved) was: fetch_tjro_pdf(date_str: str) -> Path | None:
    # The one in src.tribunais.tjro.downloader.py is fetch_tjro_pdf(target_date: date, output_dir: Path = DEFAULT_DIARIO_DIR)
    # This wrapper needs to parse the date_str.
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.warning(
            f"Invalid date format for fetch_tjro_pdf: '{date_str}'. Expected YYYY-MM-DD."
        )
        # Try to parse directly if it's already a valid ISO date string (e.g. from other parts of code)
        try:
            date_obj = datetime.date.fromisoformat(date_str)
        except ValueError:
            logger.error(f"Could not parse date '{date_str}' for fetch_tjro_pdf.")
            return None

    # Assuming _real_fetch_tjro_pdf will use its default output_dir
    pdf_path = _real_fetch_tjro_pdf(target_date=date_obj)
    return pdf_path


class GeminiExtractor:  # Wrapper class, _RealGeminiExtractor is the actual implementation
    def __init__(
        self, verbose: bool = False
    ):  # verbose is not directly used by _RealGeminiExtractor constructor
        self.logger = logging.getLogger(__name__)
        self.verbose = verbose
        self._real = _RealGeminiExtractor()

    def extract_and_save_json(
        self, pdf_path: Path, output_json_dir: Path = None, dry_run: bool = False
    ):
        self.logger.debug(f"Attempting to extract text from PDF: {pdf_path}")

        if output_json_dir is None:
            project_root_dir = Path(__file__).resolve().parent.parent
            output_json_dir = project_root_dir / "data" / "json"
        else:
            output_json_dir = Path(output_json_dir)

        output_json_dir.mkdir(parents=True, exist_ok=True)
        # Use a consistent naming scheme, perhaps including date from pdf_path if possible
        # For now, using pdf_path.stem
        output_json_path = output_json_dir / f"{pdf_path.stem}_extracted.json"

        if dry_run:
            self.logger.info(
                f"DRY-RUN: Would extract from {pdf_path} to {output_json_path}"
            )
            dummy_data = {  # Ensure this dummy data is useful for downstream dry-run steps
                "file_name_source": pdf_path.name,
                "extraction_timestamp": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
                "simulated_extraction": True,
                "decisions": [
                    {
                        "numero_processo": "DRYRUN-0000000-00.0000.0.00.0000",
                        "tipo_decisao": "simulada",
                        "polo_ativo": ["DryRun Parte Ativa"],
                        "advogados_polo_ativo": [
                            "DryRun Advogado Ativo (OAB/UF 00000)"
                        ],
                        "polo_passivo": ["DryRun Parte Passiva"],
                        "advogados_polo_passivo": [
                            "DryRun Advogado Passivo (OAB/UF 00001)"
                        ],
                        "resultado": "procedente",
                        "data_decisao": "2023-01-01",
                        "resumo": "Decisão simulada para dry run.",
                    }
                ],
            }
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(dummy_data, f, indent=2)
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
    pdf_file_path = Path(args.pdf_file)
    # Default output_json_dir to pdf_file_path.parent if not provided
    output_dir = (
        Path(args.output_json_dir) if args.output_json_dir else pdf_file_path.parent
    )

    extractor = GeminiExtractor(verbose=args.verbose)
    json_path = extractor.extract_and_save_json(
        pdf_path=pdf_file_path, output_json_dir=output_dir, dry_run=args.dry_run
    )
    if json_path:
        logger.info(f"Extract successful. JSON: {json_path}")
    else:
        logger.error("Extract failed.")
    return json_path


def _update_ratings_logic(
    logger: logging.Logger, dry_run: bool, db: CausaGanhaDB, pii_manager: PiiManager
):
    logger.info("Starting ratings update process with PII replacement.")
    if dry_run:
        logger.info(
            "DRY-RUN: Update process simulation, no DB changes will be committed."
        )

    project_root_dir = Path(__file__).resolve().parent.parent
    json_input_dir = project_root_dir / "data" / "json"
    project_root_dir / "data" / "json_processed"

    def get_rating_from_db_or_default(adv_uuid: str):
        rating_data = db.get_rating(adv_uuid)
        if rating_data:
            return CREATE_RATING_FROM_MU_SIGMA_FUNC(
                rating_data["mu"], rating_data["sigma"]
            ), rating_data["total_partidas"]
        return CREATE_NEW_RATING_FUNC(), 0

    partidas_to_add_to_db = []
    processed_files_paths = []

    if not json_input_dir.exists():
        logger.error(f"JSON input directory not found: {json_input_dir}")
        return 1
    json_files_to_process = list(json_input_dir.glob("*.json"))
    logger.debug(f"Found {len(json_files_to_process)} JSON files to process.")
    if not json_files_to_process:
        logger.info(f"No JSON files in {json_input_dir} to process.")
        return 0

    for json_path in json_files_to_process:
        logger.info(f"Processing JSON file: {json_path.name}")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                loaded_content = json.load(f)
        except Exception as e:
            logger.error(
                f"Error reading/decoding {json_path.name}: {e}. Skipping file."
            )
            continue

        decisions_in_file = loaded_content.get("decisions", [])
        logger.debug(f"Found {len(decisions_in_file)} decisions in {json_path.name}.")
        if not isinstance(decisions_in_file, list):
            logger.warning(
                f"Expected 'decisions' to be a list in {json_path.name}. Skipping."
            )
            continue

        source_pdf_filename = loaded_content.get("file_name_source", json_path.name)
        file_had_valid_decisions_for_rating = False

        for decision_data_original in decisions_in_file:
            logger.debug(
                f"Processing decision: {decision_data_original.get('numero_processo', 'N/A')}"
            )
            if not isinstance(decision_data_original, dict):
                logger.warning(
                    f"Decision data item not a dict in {json_path.name}. Skipping: {decision_data_original}"
                )
                continue

            decision_data_pii_replaced = decision_data_original.copy()

            if not validate_decision(decision_data_original):
                logger.warning(
                    f"Invalid decision in {json_path.name} (processo: {decision_data_original.get('numero_processo', 'N/A')}). Skipping."
                )
                continue

            # PII Replacement: numero_processo
            original_case_no_str = str(
                decision_data_original.get("numero_processo", "")
            )
            uuid_case_no = pii_manager.get_or_create_pii_mapping(
                original_case_no_str, "CASE_NUMBER", original_case_no_str
            )
            decision_data_pii_replaced["numero_processo"] = (
                uuid_case_no  # Replace original field
            )

            # PII Replacement: polo_ativo, polo_passivo
            for polo_key_orig in ["polo_ativo", "polo_passivo"]:
                orig_polo_list = decision_data_original.get(polo_key_orig, [])
                if isinstance(orig_polo_list, str):
                    orig_polo_list = [orig_polo_list]
                uuid_list = [
                    pii_manager.get_or_create_pii_mapping(
                        str(name), "PARTY_NAME", str(name)
                    )
                    for name in orig_polo_list
                    if name and str(name).strip()
                ]
                decision_data_pii_replaced[polo_key_orig] = (
                    uuid_list  # Replace original field
                )

            # PII Replacement: advogados_polo_ativo, advogados_polo_passivo
            # These lists will store UUIDs of the full lawyer strings for the PII-replaced JSON
            advs_polo_ativo_full_str_uuids_for_json = []
            advs_polo_passivo_full_str_uuids_for_json = []

            # These are needed for ratings logic (UUIDs of normalized lawyer names)
            adv_teams_rating_uuids = {}

            for adv_str_orig in decision_data_original.get("advogados_polo_ativo", []):
                adv_clean = str(adv_str_orig).strip()
                if not adv_clean:
                    continue
                norm_id = normalize_lawyer_name(adv_clean)
                if not norm_id:
                    continue

                rating_uuid = pii_manager.get_or_create_pii_mapping(
                    norm_id, "LAWYER_ID_NORMALIZED", norm_id
                )
                adv_teams_rating_uuids.setdefault("team_a", []).append(rating_uuid)

                full_str_uuid = pii_manager.get_or_create_pii_mapping(
                    adv_clean, "LAWYER_FULL_STRING", adv_clean
                )
                advs_polo_ativo_full_str_uuids_for_json.append(full_str_uuid)

            for adv_str_orig in decision_data_original.get(
                "advogados_polo_passivo", []
            ):
                adv_clean = str(adv_str_orig).strip()
                if not adv_clean:
                    continue
                norm_id = normalize_lawyer_name(adv_clean)
                if not norm_id:
                    continue

                rating_uuid = pii_manager.get_or_create_pii_mapping(
                    norm_id, "LAWYER_ID_NORMALIZED", norm_id
                )
                adv_teams_rating_uuids.setdefault("team_b", []).append(rating_uuid)

                full_str_uuid = pii_manager.get_or_create_pii_mapping(
                    adv_clean, "LAWYER_FULL_STRING", adv_clean
                )
                advs_polo_passivo_full_str_uuids_for_json.append(full_str_uuid)

            # Update the original lawyer fields in decision_data_pii_replaced to hold UUIDs of full strings
            decision_data_pii_replaced["advogados_polo_ativo"] = (
                advs_polo_ativo_full_str_uuids_for_json
            )
            decision_data_pii_replaced["advogados_polo_passivo"] = (
                advs_polo_passivo_full_str_uuids_for_json
            )

            # Store rating UUIDs separately in the PII-replaced JSON if needed for context, or for other downstream processes
            # that might consume this raw_json. These are not PII themselves.
            decision_data_pii_replaced["advogados_polo_ativo_rating_uuids"] = (
                adv_teams_rating_uuids.get("team_a", [])
            )
            decision_data_pii_replaced["advogados_polo_passivo_rating_uuids"] = (
                adv_teams_rating_uuids.get("team_b", [])
            )
            # (The old code created separate vars advs_polo_ativo_full_str_uuids and added them as new keys,
            # now we are overwriting original keys like "advogados_polo_ativo")

            if not dry_run:
                try:
                    db.add_raw_decision(
                        numero_processo_uuid=uuid_case_no,  # This is the UUID of the case number itself
                        json_source_file=json_path.name,
                        polo_ativo_uuids_json=json.dumps(
                            decision_data_pii_replaced.get("polo_ativo", [])
                        ),  # Now contains UUIDs
                        polo_passivo_uuids_json=json.dumps(
                            decision_data_pii_replaced.get("polo_passivo", [])
                        ),  # Now contains UUIDs
                        advogados_polo_ativo_full_str_uuids_json=json.dumps(
                            decision_data_pii_replaced.get("advogados_polo_ativo", [])
                        ),  # Now contains full string UUIDs
                        advogados_polo_passivo_full_str_uuids_json=json.dumps(
                            decision_data_pii_replaced.get("advogados_polo_passivo", [])
                        ),  # Now contains full string UUIDs
                        tipo_decisao=decision_data_original.get(
                            "tipo_decisao"
                        ),  # Keep original non-PII fields
                        resultado_original=decision_data_original.get(
                            "resultado"
                        ),  # Keep original non-PII fields
                        data_decisao_original=decision_data_original.get("data_decisao")
                        or decision_data_original.get("data"),
                        resumo_original=decision_data_original.get("resumo"),
                        raw_json_pii_replaced=json.dumps(decision_data_pii_replaced),
                        validation_status="valid",
                        extraction_timestamp=loaded_content.get("extraction_timestamp"),
                        pdf_source_file=source_pdf_filename,  # Added this field
                    )
                except Exception as e_db_dec:
                    logger.error(
                        f"DB save error for decision {uuid_case_no}: {e_db_dec}",
                        exc_info=True,
                    )
                    return 1

            final_team_a_ids = sorted(
                list(set(adv_teams_rating_uuids.get("team_a", [])))
            )
            final_team_b_ids = sorted(
                list(set(adv_teams_rating_uuids.get("team_b", [])))
            )

            logger.debug(f"Final team A IDs: {final_team_a_ids}")
            logger.debug(f"Final team B IDs: {final_team_b_ids}")

            if not final_team_a_ids or not final_team_b_ids:
                logger.warning(
                    f"Missing lawyer UUIDs for rating {original_case_no_str}. Skip rating."
                )
                continue
            if set(final_team_a_ids) == set(final_team_b_ids):
                logger.info(
                    f"Identical teams (UUIDs) for {original_case_no_str}. Skip rating."
                )
                continue

            res_raw = decision_data_original.get("resultado", "").lower()
            outcome = MatchResult.DRAW
            if res_raw in ["procedente", "provido", "confirmada"]:
                outcome = MatchResult.WIN_A
            elif res_raw in ["improcedente", "negado_provimento", "reformada"]:
                outcome = MatchResult.WIN_B

            team_a_ratings_before = [
                get_rating_from_db_or_default(uid)[0] for uid in final_team_a_ids
            ]
            team_b_ratings_before = [
                get_rating_from_db_or_default(uid)[0] for uid in final_team_b_ids
            ]

            partida_a_antes = {
                uid: (r.mu, r.sigma)
                for uid, r in zip(final_team_a_ids, team_a_ratings_before)
            }
            partida_b_antes = {
                uid: (r.mu, r.sigma)
                for uid, r in zip(final_team_b_ids, team_b_ratings_before)
            }

            new_a_ratings, new_b_ratings = UPDATE_RATINGS_FUNC(
                RATING_MODEL_INSTANCE,
                team_a_ratings_before,
                team_b_ratings_before,
                outcome,
            )

            if not dry_run:
                try:
                    for i, uid in enumerate(final_team_a_ids):
                        db.update_rating(
                            uid, new_a_ratings[i].mu, new_a_ratings[i].sigma
                        )
                    for i, uid in enumerate(final_team_b_ids):
                        db.update_rating(
                            uid, new_b_ratings[i].mu, new_b_ratings[i].sigma
                        )
                except Exception as e_db_rate:
                    logger.error(
                        f"DB rating update error for {uuid_case_no}: {e_db_rate}",
                        exc_info=True,
                    )
                    return 1

            partidas_to_add_to_db.append(
                {
                    "data_partida": decision_data_original.get("data_decisao")
                    or decision_data_original.get("data")
                    or datetime.date.today().isoformat(),
                    "numero_processo": uuid_case_no,
                    "equipe_a_ids": final_team_a_ids,
                    "equipe_b_ids": final_team_b_ids,
                    "ratings_antes_a": partida_a_antes,
                    "ratings_antes_b": partida_b_antes,
                    "resultado": outcome.value,  # Changed from "resultado_partida" to match add_partida signature
                    "ratings_depois_a": {
                        uid: (r.mu, r.sigma)
                        for uid, r in zip(final_team_a_ids, new_a_ratings)
                    },
                    "ratings_depois_b": {
                        uid: (r.mu, r.sigma)
                        for uid, r in zip(final_team_b_ids, new_b_ratings)
                    },
                }
            )
            file_had_valid_decisions_for_rating = True

    print(f"file_had_valid_decisions_for_rating: {file_had_valid_decisions_for_rating}")
    if file_had_valid_decisions_for_rating:
        processed_files_paths.append(json_path)
    print(f"processed_files_paths: {processed_files_paths}")


def update_command(args):
    logger = logging.getLogger(__name__)
    logger.debug(f"Update command called with args: {args}")
    db_instance = None
    try:
        db_instance = CausaGanhaDB()
        db_instance.connect()
        pii_manager = PiiManager(db_instance.conn)
        _update_ratings_logic(logger, args.dry_run, db_instance, pii_manager)
        return 0
    except Exception as e:
        logger.critical(f"Failed during update command: {e}", exc_info=True)
        return 1
    finally:
        if db_instance and hasattr(db_instance, "conn") and db_instance.conn:
            db_instance.close()


def run_command(args):
    logger = logging.getLogger(__name__)
    logger.debug(f"Run command called with args: {args}")

    # Pass verbose to collect_command and extract_command
    collect_args = argparse.Namespace(
        date=args.date,
        dry_run=args.dry_run,
        verbose=args.verbose if hasattr(args, "verbose") else False,
    )
    pdf_path = collect_command(collect_args)
    if not pdf_path:
        logger.error(f"'collect' failed for {args.date}. Aborting 'run'.")
        return 1

    project_root_dir = Path(__file__).resolve().parent.parent
    default_json_out_dir = project_root_dir / "data" / "json"
    extract_output_dir = (
        Path(args.output_json_dir) if args.output_json_dir else default_json_out_dir
    )

    extract_args = argparse.Namespace(
        pdf_file=pdf_path,
        output_json_dir=extract_output_dir,
        dry_run=args.dry_run,
        verbose=args.verbose if hasattr(args, "verbose") else False,
    )
    json_output_path = extract_command(extract_args)
    if not json_output_path:
        logger.error(f"'extract' failed for {pdf_path}. Aborting 'run'.")
        return 1

    db_instance_run = None
    try:
        db_instance_run = CausaGanhaDB()
        db_instance_run.connect()
        pii_manager_run = PiiManager(db_instance_run.conn)
        logger.info("Starting 'update' as part of 'run'...")
        update_result = _update_ratings_logic(
            logger, args.dry_run, db_instance_run, pii_manager_run
        )
        if update_result != 0:
            logger.critical("'update' failed as part of 'run' command.")
            return 1
        logger.info(f"Run command completed for {args.date}.")
        return 0
    except Exception as e:
        logger.critical(
            f"Failed during 'update' part of 'run' command: {e}", exc_info=True
        )
        return 1
    finally:
        if (
            db_instance_run
            and hasattr(db_instance_run, "conn")
            and db_instance_run.conn
        ):
            db_instance_run.close()


def archive_command(args):
    logger = logging.getLogger(__name__)
    logger.debug(f"Archive command: {args}")
    if args.dry_run:
        logger.info(
            f"DRY-RUN: Archive: type={args.archive_type}, date={args.date or 'today'}, db={args.db_path}"
        )
        return 0
    try:
        from src.archive_db import DatabaseArchiver, IAConfig

        snap_date = (
            datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
            if args.date
            else datetime.date.today()
        )
        logger.info(
            f"Starting archive: type={args.archive_type}, date={snap_date}, db={args.db_path}"
        )
        if not args.db_path.exists():
            logger.error(f"DB not found: {args.db_path}")
            return 1
        archiver = DatabaseArchiver(IAConfig.from_env())
        if archiver.archive_database(
            db_path=args.db_path,
            snapshot_date=snap_date,
            archive_type=args.archive_type,
        ):
            logger.info("✅ Database archive completed successfully")
            return 0
        else:
            logger.error("❌ Database archive failed")
            return 1
    except ImportError as e:
        logger.error(f"Archive import error: {e}. 'internetarchive' installed?")
        return 1
    except ValueError as e:
        logger.error(f"Archive config error: {e}. Check IA env vars.")
        return 1
    except Exception as e:
        logger.error(
            f"Archive command failed: {e}",
            exc_info=args.verbose if hasattr(args, "verbose") else False,
        )
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="CausaGanha Legal Rating ETL Pipeline."
    )
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logging.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Commands")
    cmd_defs = [
        (
            "collect",
            "Downloads documents.",
            collect_command,
            [("--date", {"required": True}), ("--dry-run", {"action": "store_true"})],
        ),
        (
            "extract",
            "Extracts PDF to JSON.",
            extract_command,
            [
                ("--pdf_file", {"required": True, "type": Path}),
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
                ("--date", {}),
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
            "Full pipeline.",
            run_command,
            [
                ("--date", {"required": True}),
                ("--output_json_dir", {"type": Path}),
                ("--dry-run", {"action": "store_true"}),
            ],
        ),
    ]
    for name, help_text, func, arg_list in cmd_defs:
        p = subparsers.add_parser(name, help=help_text)
        p.set_defaults(func=func)
        # Add verbose to all subparsers for consistency if it's a global option
        p.add_argument(
            "--verbose",
            action="store_true",
            help="Enable DEBUG logging for this command.",
        )
        for arg_name, params in arg_list:
            p.add_argument(arg_name, **params)

    args = parser.parse_args()
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)
    logger.debug(f"Command: {args.command}, Args: {vars(args)}")
    if hasattr(args, "func"):
        return args.func(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    main()
