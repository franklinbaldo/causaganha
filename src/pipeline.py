import argparse
import logging
from pathlib import Path
import sys
import json
import datetime

# Change to absolute imports from 'src' package
from src.downloader import fetch_tjro_pdf as _real_fetch_tjro_pdf
from src.extractor import GeminiExtractor as _RealGeminiExtractor

try:
    from src.utils import normalize_lawyer_name, validate_decision
    from src.config import load_config
    from src.openskill_rating import (
        get_openskill_model,
        create_rating as create_openskill_rating_object,
        rate_teams as update_openskill_ratings,
    )
    from enum import Enum

    class MatchResult(Enum):
        WIN_A = "win_a"
        WIN_B = "win_b"
        DRAW = "draw"
        PARTIAL_A = "partial_a"
        PARTIAL_B = "partial_b"

    CONFIG = load_config()
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

    CRITICAL_IMPORTS_FAILED = False
except ImportError as e:
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.CRITICAL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s (pipeline_import_error)",
    )
    logging.critical(
        f"Failed to import critical modules in pipeline.py: {e}. Pipeline functions will be no-ops."
    )
    CRITICAL_IMPORTS_FAILED = True

    def _no_op_func_for_pipeline_stub(*args, **kwargs):
        logging.error("Pipeline dependency missing, function is no-op.")
        return None

    fetch_tjro_pdf = _no_op_func_for_pipeline_stub
    GeminiExtractor = type(
        "NoOpGeminiExtractor",
        (),
        {
            "extract_and_save_json": _no_op_func_for_pipeline_stub,
            "__init__": lambda self, verbose=False: None,
        },
    )
    update_command = _no_op_func_for_pipeline_stub
    collect_command = _no_op_func_for_pipeline_stub
    extract_command = _no_op_func_for_pipeline_stub
    run_command = _no_op_func_for_pipeline_stub
    archive_command = _no_op_func_for_pipeline_stub

    def main():
        return logging.critical(
            "Pipeline main() cannot run due to missing critical imports."
        )


if not CRITICAL_IMPORTS_FAILED:  # Define actual functions only if imports succeeded

    def fetch_tjro_pdf(
        date_str: str, dry_run: bool = False, verbose: bool = False
    ) -> Optional[Path]:
        logger_func = logging.getLogger(__name__)
        if dry_run:
            logger_func.info(f"DRY-RUN: Would fetch TJRO PDF for date: {date_str}")
            return Path(f"/tmp/fake_tjro_{date_str.replace('-', '')}.pdf")  # nosec
        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            logger_func.warning(f"Invalid date '{date_str}', attempting direct pass")
            try:
                date_obj = datetime.date.fromisoformat(date_str)
            except ValueError:
                logger_func.error("Could not parse date '%s'", date_str)
                return None
        pdf_path = _real_fetch_tjro_pdf(date_obj)
        return pdf_path

    class GeminiExtractor:  # Wrapper class
        def __init__(self, verbose: bool = False):
            self.logger = logging.getLogger(__name__)
            self.verbose = verbose
            self._real = _RealGeminiExtractor(
                api_key=CONFIG.get("gemini", {}).get("api_key"),
                model_name=CONFIG.get("gemini", {}).get("model_name"),
            )

        def extract_and_save_json(
            self,
            pdf_path: Path,
            output_json_dir: Optional[Path] = None,
            dry_run: bool = False,
        ) -> Optional[Path]:
            self.logger.debug(f"Attempting to extract text from PDF: {pdf_path}")
            final_output_json_dir = (
                Path(output_json_dir)
                if output_json_dir
                else pdf_path.parent / "json_extracted"
            )
            final_output_json_dir.mkdir(parents=True, exist_ok=True)

            output_json_path = final_output_json_dir / f"{pdf_path.stem}_extracted.json"
            if dry_run:
                self.logger.info(
                    f"DRY-RUN: Would extract from {pdf_path} to {output_json_path}"
                )
                with open(output_json_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "file_name_source": pdf_path.name,
                            "simulated_extraction": True,
                            "decisions": [],
                        },
                        f,
                        indent=2,
                    )
                return output_json_path
            return self._real.extract_and_save_json(pdf_path, final_output_json_dir)

    def setup_logging(verbose: bool):
        log_level = logging.DEBUG if verbose else logging.INFO
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.basicConfig(
            stream=sys.stdout,
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s (pipeline_setup)",
        )
        logging.getLogger("httpx").setLevel(logging.WARNING)

    def collect_command(args: argparse.Namespace):
        logger_cmd = logging.getLogger(__name__)
        logger_cmd.debug(f"Collect command called with: {args}")
        pdf_path = fetch_tjro_pdf(
            date_str=args.date, dry_run=args.dry_run, verbose=args.verbose
        )
        if pdf_path:
            logger_cmd.info(f"Collect successful. PDF available at: {pdf_path}")
        else:
            logger_cmd.error(f"Collect command failed for date {args.date}.")
        return pdf_path

    def extract_command(args: argparse.Namespace):
        logger_cmd = logging.getLogger(__name__)
        logger_cmd.debug(f"Extract command called with: {args}")
        pdf_file_path = Path(args.pdf_file)
        output_dir = (
            Path(args.output_json_dir) if args.output_json_dir else pdf_file_path.parent
        )

        extractor = GeminiExtractor(verbose=args.verbose)
        json_path = extractor.extract_and_save_json(
            pdf_path=pdf_file_path, output_json_dir=output_dir, dry_run=args.dry_run
        )
        if json_path:
            logger_cmd.info(f"Extract successful. JSON saved to: {json_path}")
        else:
            logger_cmd.error(f"Extract command failed for PDF: {args.pdf_file}")
        return json_path

    def _update_ratings_logic(logger_func: logging.Logger, dry_run: bool):
        logger_func.info("Starting OpenSkill ratings update process.")
        if dry_run:
            logger_func.info(
                "DRY-RUN: OpenSkill update process simulation, no files changed."
            )

        base_data_path = Path(CONFIG.get("data_dir", "data"))
        json_input_dir = base_data_path / "json"
        processed_json_dir = base_data_path / "json_processed"
        base_data_path / "ratings.csv"
        base_data_path / "partidas.csv"

        json_input_dir.mkdir(parents=True, exist_ok=True)
        processed_json_dir.mkdir(parents=True, exist_ok=True)

        logger_func.info(
            "Placeholder for full _update_ratings_logic - actual logic omitted for brevity in this example."
        )
        # Full logic for reading CSVs, processing JSONs, updating ratings, saving CSVs, moving files would go here.

    def update_command(args: argparse.Namespace):
        logger_cmd = logging.getLogger(__name__)
        logger_cmd.debug(f"Update command called with args: {args}")
        _update_ratings_logic(logger_cmd, args.dry_run)

    def run_command(args: argparse.Namespace):
        logger_cmd = logging.getLogger(__name__)
        logger_cmd.debug(f"Run command called with args: {args}")
        logger_cmd.info(f"Starting 'collect' step for date {args.date}...")
        pdf_path = collect_command(
            argparse.Namespace(
                date=args.date, dry_run=args.dry_run, verbose=args.verbose
            )
        )

        if not pdf_path:
            logger_cmd.error(
                f"'collect' failed for {args.date}. Aborting 'run' command."
            )
            return
        logger_cmd.info(f"'collect' successful. PDF is at: {pdf_path}")
        logger_cmd.info(f"Starting 'extract' for PDF {pdf_path}...")

        extract_output_dir_val = (
            args.output_json_dir
            if hasattr(args, "output_json_dir") and args.output_json_dir
            else Path(CONFIG.get("data_dir", "data")) / "json"
        )
        json_output_path = extract_command(
            argparse.Namespace(
                pdf_file=pdf_path,
                output_json_dir=extract_output_dir_val,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
        )

        if not json_output_path:
            logger_cmd.error(
                f"'extract' failed for {pdf_path}. 'run' command partially completed."
            )
            return
        logger_cmd.info(f"'extract' successful. JSON output at: {json_output_path}")
        logger_cmd.info("Starting 'update' ratings step as part of 'run' command...")
        update_command(argparse.Namespace(dry_run=args.dry_run, verbose=args.verbose))
        logger_cmd.info(f"Run command completed for date {args.date}.")

    def archive_command(args: argparse.Namespace):
        logger_cmd = logging.getLogger(__name__)
        logger_cmd.info(f"Archive command (stub) called with: {args}")  # Stub for now

    def main():
        parser = argparse.ArgumentParser(
            description="CausaGanha Legal Rating ETL Pipeline."
        )
        parser.add_argument(
            "--verbose", action="store_true", help="Enable DEBUG logging."
        )
        subparsers = parser.add_subparsers(
            dest="command", required=True, help="Command to execute"
        )

        cmd_defs = [
            (
                "collect",
                "Downloads Diarios for a specific date.",
                collect_command,
                [
                    ("--date", {"required": True}),
                    ("--dry-run", {"action": "store_true"}),
                ],
            ),
            (
                "extract",
                "Extracts data from a PDF to JSON.",
                extract_command,
                [
                    ("--pdf_file", {"type": Path, "required": True}),
                    ("--output_json_dir", {"type": Path}),
                    ("--dry-run", {"action": "store_true"}),
                ],
            ),
            (
                "update",
                "Updates OpenSkill ratings from processed JSON files.",
                update_command,
                [("--dry-run", {"action": "store_true"})],
            ),
            (
                "archive",
                "Archives database snapshot.",
                archive_command,
                [
                    ("--date", {}),
                    (
                        "--archive-type",
                        {"choices": ["weekly", "monthly"], "default": "weekly"},
                    ),
                    (
                        "--db-path",
                        {
                            "type": Path,
                            "default": Path(CONFIG.get("data_dir", "data"))
                            / "causaganha.duckdb",
                        },
                    ),
                    ("--dry-run", {"action": "store_true"}),
                ],
            ),
            (
                "run",
                "Runs the full pipeline (collect, extract, update).",
                run_command,
                [
                    ("--date", {"required": True}),
                    ("--output_json_dir", {"type": Path}),
                    ("--dry-run", {"action": "store_true"}),
                ],
            ),
        ]

        for name, help_txt, func, arg_list in cmd_defs:
            p = subparsers.add_parser(name, help=help_txt)
            p.set_defaults(func=func)
            for arg_name, params in arg_list:
                p.add_argument(arg_name, **params)

        args = parser.parse_args()
        setup_logging(args.verbose if hasattr(args, "verbose") else False)

        logger_main = logging.getLogger(__name__)
        logger_main.debug(
            f"Executing command: {args.command} with arguments: {vars(args)}"
        )

        if hasattr(args, "func"):
            args.func(args)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
