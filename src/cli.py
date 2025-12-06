"""CausaGanha CLI - Modern command-line interface for judicial document processing."""

import asyncio
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import duckdb
import typer

from config import load_config
from database import CausaGanhaDB, DatabaseManager, run_db_migrations
from simple_backup import backup_database_before_changes, export_and_upload_to_ia
from utils import (
    extract_tribunal_from_url,
    validate_tribunal_url,
    extract_date_from_url,
    extract_tribunal_code_from_url,
    normalize_lawyer_name,
)
from models.diario import Diario

from async_diario_pipeline import main as async_pipeline_main, AsyncDiarioPipeline

logger = logging.getLogger(__name__)


# Custom Pipeline class to sync with DB
class DBAsyncPipeline(AsyncDiarioPipeline):
    def __init__(self, db: CausaGanhaDB, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = db

    async def process_diario(self, diario_data, skip_existing=True):
        result = await super().process_diario(diario_data, skip_existing)
        status_obj = self.status_tracker.get(diario_data["ia_identifier"])
        if status_obj:
            new_status = status_obj.status
            # Map pipeline status to DB status
            db_status = new_status
            if new_status == "completed":
                db_status = "archived"

            # Update DB
            self.db.update_diario_status(
                diario_data["full_url"],
                db_status,
                ia_identifier=status_obj.ia_identifier,
                error_message=status_obj.error_message,
                arquivo_path=status_obj.local_path,
            )
        return result

app = typer.Typer(
    name="causaganha",
    help="Judicial document processing pipeline with OpenSkill rating system.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)

# Subcommand groups
pipeline_app = typer.Typer(help="Pipeline operations")
app.add_typer(pipeline_app, name="pipeline")

cg_config = load_config()

db_manager_global: Optional[DatabaseManager] = None
cg_db_global: Optional[CausaGanhaDB] = None

CTX_DB_MANAGER = "db_manager"
CTX_CG_DB = "cg_db"
CTX_DB_PATH_CFG = "db_path_cfg"


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    global db_manager_global, cg_db_global

    if ctx.resilient_parsing or (hasattr(ctx, "obj") and ctx.obj is not None):
        return

    db_path_str = cg_config.get("database", {}).get("path", "data/causaganha.duckdb")
    db_path = Path(db_path_str)
    ctx.obj = {CTX_DB_PATH_CFG: db_path}

    if ctx.invoked_subcommand == "db":
        action_param = ctx.params.get("action", "").lower() if ctx.params else ""
        if action_param in ["migrate", "reset"]:
            logger.info(
                f"Delaying full DB objects initialization for 'db {action_param}'."
            )
            return

    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_manager_global = DatabaseManager(db_path)
        cg_db_global = CausaGanhaDB(db_manager_global)

        ctx.obj[CTX_DB_MANAGER] = db_manager_global
        ctx.obj[CTX_CG_DB] = cg_db_global
        logger.info(
            f"Global DatabaseManager and CausaGanhaDB initialized for: {db_path}"
        )

    except Exception as e:
        logger.critical(
            f"Failed to initialize global DatabaseManager/CausaGanhaDB: {e}",
            exc_info=True,
        )
        typer.echo(f"❌ CRITICAL ERROR: Database initialization failed: {e}", err=True)
        raise typer.Exit(code=100)


def get_cg_db_from_ctx(ctx: typer.Context) -> CausaGanhaDB:
    if (
        hasattr(ctx, "obj")
        and ctx.obj
        and isinstance(ctx.obj.get(CTX_CG_DB), CausaGanhaDB)
    ):
        return ctx.obj[CTX_CG_DB]

    logger.warning(
        f"CausaGanhaDB requested but not in Typer context. Attempting dynamic init. Command: {ctx.invoked_subcommand}"
    )
    db_path_cfg = (
        ctx.obj.get(CTX_DB_PATH_CFG)
        if hasattr(ctx, "obj") and ctx.obj
        else Path(cg_config["database"]["path"])
    )

    if not db_path_cfg.exists() and ctx.invoked_subcommand != "db":
        typer.echo(
            f"❌ Database file {db_path_cfg} does not exist. Run 'db migrate' first.",
            err=True,
        )
        raise typer.Exit(103)

    try:
        manager = DatabaseManager(Path(db_path_cfg))
        cg_db_instance = CausaGanhaDB(manager)
        if hasattr(ctx, "obj") and ctx.obj:
            ctx.obj[CTX_DB_MANAGER] = manager
            ctx.obj[CTX_CG_DB] = cg_db_instance
        else:
            ctx.obj = {
                CTX_DB_MANAGER: manager,
                CTX_CG_DB: cg_db_instance,
                CTX_DB_PATH_CFG: db_path_cfg,
            }
        logger.info(
            f"Dynamically initialized CausaGanhaDB for command {ctx.invoked_subcommand}"
        )
        return cg_db_instance
    except Exception as e:
        logger.critical(
            f"Dynamic DB initialization failed for command {ctx.invoked_subcommand}: {e}",
            exc_info=True,
        )
        typer.echo(
            f"❌ Critical: Dynamic database initialization failed: {e}", err=True
        )
        raise typer.Exit(101)


def get_db_manager_from_ctx(ctx: typer.Context) -> DatabaseManager:
    if (
        hasattr(ctx, "obj")
        and ctx.obj
        and isinstance(ctx.obj.get(CTX_DB_MANAGER), DatabaseManager)
    ):
        return ctx.obj[CTX_DB_MANAGER]
    get_cg_db_from_ctx(ctx)
    if (
        hasattr(ctx, "obj")
        and ctx.obj
        and isinstance(ctx.obj.get(CTX_DB_MANAGER), DatabaseManager)
    ):
        return ctx.obj[CTX_DB_MANAGER]
    logger.error("DatabaseManager not found in context after dynamic init attempt.")
    typer.echo("❌ Critical: Database Manager could not be initialized.", err=True)
    raise typer.Exit(102)


# This is the old global 'db' instance. It's kept temporarily for commands
# that are not yet refactored.
original_db_path_for_stub = Path(cg_config["database"]["path"])
original_db_manager_for_stub = DatabaseManager(original_db_path_for_stub)
db = CausaGanhaDB(original_db_manager_for_stub)  # Old global 'db' needs a manager too
logger.warning(
    "Old global 'db' instance created. Unrefactored commands using it might behave unexpectedly."
)




# --- Stubs for commands not yet refactored ---
@app.command()
def queue(
    ctx: typer.Context,
    url: Optional[str] = typer.Option(None, help="Direct URL of the diario to queue"),
    from_csv: Optional[Path] = typer.Option(
        None, help="Path to CSV file containing URLs"
    ),
) -> None:
    """Queue judicial documents for processing."""
    cg_db = get_cg_db_from_ctx(ctx)

    if not url and not from_csv:
        typer.echo("❌ URL or CSV file needed. Use --url or --from-csv.", err=True)
        raise typer.Exit(1)

    diarios_to_queue = []

    # Handle single URL
    if url:
        # Validate URL
        if not validate_tribunal_url(url):
            typer.echo(
                f"❌ Invalid URL: {url} - not a valid tribunal URL (must be .jus.br)",
                err=True,
            )
            raise typer.Exit(1)

        # Extract Date
        date_str = extract_date_from_url(url)
        if not date_str:
            typer.echo(f"❌ Could not extract date from URL: {url}", err=True)
            raise typer.Exit(1)

        tribunal_code = extract_tribunal_code_from_url(url)

        from datetime import date as date_obj

        d = Diario(
            tribunal=tribunal_code,
            data=date_obj.fromisoformat(date_str),
            url=url,
            status="pending",
        )
        diarios_to_queue.append(d)

    # Handle CSV
    if from_csv:
        if not from_csv.exists():
            typer.echo(f"❌ CSV file not found: {from_csv}", err=True)
            raise typer.Exit(1)

        try:
            import pandas as pd

            # Assuming CSV has a 'url' column or just a list of URLs
            # Try reading with header, if 'url' exists use it, else assume first col
            df = pd.read_csv(from_csv)
            urls = []
            if "url" in df.columns:
                urls = df["url"].tolist()
            else:
                urls = df.iloc[:, 0].tolist()

            for csv_url in urls:
                if not isinstance(csv_url, str):
                    continue
                csv_url = csv_url.strip()
                if not csv_url:
                    continue

                if not validate_tribunal_url(csv_url):
                    logger.warning(f"Skipping invalid URL from CSV: {csv_url}")
                    continue

                d_str = extract_date_from_url(csv_url)
                if not d_str:
                    logger.warning(f"Skipping URL with no date from CSV: {csv_url}")
                    continue

                t_code = extract_tribunal_code_from_url(csv_url)
                from datetime import date as date_obj

                d_obj = Diario(
                    tribunal=t_code,
                    data=date_obj.fromisoformat(d_str),
                    url=csv_url,
                    status="pending",
                )
                diarios_to_queue.append(d_obj)

        except Exception as e:
            typer.echo(f"❌ Error reading CSV: {e}", err=True)
            raise typer.Exit(1)

    # Queue items
    count = 0
    with cg_db.db_manager:  # ensure connection
        for diario in diarios_to_queue:
            if cg_db.queue_diario(diario):
                typer.echo(f"✅ Queued: {diario.display_name}")
                count += 1
            else:
                typer.echo(f"❌ Failed to queue: {diario.url}", err=True)

    if count == 0 and (url or from_csv):
        # If we had inputs but failed to queue anything
        if url:  # Specific single URL failure should exit 1
            raise typer.Exit(1)
        # For CSV, if at least some were skipped but maybe not all failed explicitly?
        # If 0 queued, maybe warning.
        if len(diarios_to_queue) > 0:  # Tried to queue but failed
            raise typer.Exit(1)


@app.command()
def archive(
    ctx: typer.Context,
    limit: Optional[int] = typer.Option(None, help="Limit number of items to archive"),
    force: bool = typer.Option(False, help="Force re-archiving even if exists"),
) -> None:
    """Download and archive queued documents to Internet Archive."""
    cg_db = get_cg_db_from_ctx(ctx)

    # Get pending items
    diarios = cg_db.get_diarios_by_status("pending")
    if not diarios:
        typer.echo("No pending items to archive.")
        return

    typer.echo(f"Found {len(diarios)} pending items.")

    # Convert to format for pipeline
    pipeline_data = []
    for d in diarios:
        # Generate ia_identifier if missing
        ia_id = d.ia_identifier
        if not ia_id:
            # Simple generation strategy
            filename_part = (
                d.filename if d.filename else f"diario_{d.data.strftime('%Y%m%d')}.pdf"
            )
            # Sanitize filename part
            filename_part = re.sub(r"[^a-zA-Z0-9_\-\.]", "", filename_part)
            ia_id = (
                f"{d.tribunal}-diario-{d.data.strftime('%Y-%m-%d')}-{filename_part}"
            )

        item = {
            "ia_identifier": ia_id,
            "original_filename": d.filename
            or f"diario_{d.data.strftime('%Y%m%d')}.pdf",
            "full_url": d.url,
            "date": d.data.isoformat(),
            "metadata": d.metadata,
        }
        pipeline_data.append(item)

    if limit:
        pipeline_data = pipeline_data[:limit]
        typer.echo(f"Processing {len(pipeline_data)} items (limit applied).")

    async def run_archiver():
        # Setup temporary directory for pipeline data if needed, or use default data dir
        data_dir = Path("data")
        progress_file = data_dir / "archive_cmd_progress.json"

        async with DBAsyncPipeline(
            db=cg_db,
            data_dir=data_dir,
            progress_file=progress_file,
            try_direct_upload=True,
        ) as pipeline:
            await pipeline.run_pipeline(pipeline_data, skip_existing=not force)

    try:
        asyncio.run(run_archiver())
        typer.echo("✅ Archive process finished.")
    except Exception as e:
        typer.echo(f"❌ Archive process failed: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def analyze(
    ctx: typer.Context,
    limit: Optional[int] = typer.Option(None, help="Limit number of items to analyze"),
    force: bool = typer.Option(False, help="Force re-analysis"),
) -> None:
    """Extract information from archived documents using Gemini."""
    cg_db = get_cg_db_from_ctx(ctx)
    from extractor import GeminiExtractor

    # Get archived items
    diarios = cg_db.get_diarios_by_status("archived")
    if not diarios:
        # Fallback to 'downloaded' if archive step skipped upload?
        diarios = cg_db.get_diarios_by_status("downloaded")

    if not diarios:
        typer.echo("No items ready for analysis (archived/downloaded).")
        return

    if limit:
        diarios = diarios[:limit]

    extractor = GeminiExtractor()
    print(f"DEBUG: extractor is {extractor}")
    if not extractor.is_configured():
        typer.echo(
            "⚠️ Gemini not configured. Using dummy data/extraction might fail.", err=True
        )

    output_dir = Path("data/json_extracted")
    output_dir.mkdir(exist_ok=True)

    for d in diarios:
        # Check if JSON already exists in metadata
        if (
            not force
            and d.metadata.get("json_path")
            and Path(d.metadata["json_path"]).exists()
        ):
            typer.echo(f"Skipping {d.display_name} (already analyzed)")
            continue

        typer.echo(f"Analyzing {d.display_name}...")

        # Locate PDF
        pdf_path = None
        temp_pdf = None

        # Check local path if set
        if d.pdf_path and d.pdf_path.exists():
            pdf_path = d.pdf_path
        else:
            # Download from IA or Original URL
            # Prefer IA if identifier exists
            download_url = None
            if d.ia_identifier and d.filename:
                download_url = (
                    f"https://archive.org/download/{d.ia_identifier}/{d.filename}"
                )
            elif d.url:
                download_url = d.url

            if download_url:
                try:
                    # Download to temp
                    import tempfile
                    import os

                    fd, temp_path = tempfile.mkstemp(suffix=".pdf")
                    os.close(fd)
                    temp_pdf = Path(temp_path)

                    typer.echo(f"  Downloading from {download_url}...")
                    # Simple sync download for now
                    resp = requests.get(download_url, timeout=30)
                    resp.raise_for_status()
                    with open(temp_pdf, "wb") as f:
                        f.write(resp.content)
                    pdf_path = temp_pdf
                except Exception as e:
                    typer.echo(f"  ❌ Download failed: {e}", err=True)
                    continue
            else:
                typer.echo("  ❌ No URL to download PDF.", err=True)
                continue

        if pdf_path:
            try:
                json_path = extractor.extract_and_save_json(pdf_path, output_dir)
                if json_path:
                    # Update DB
                    d.metadata["json_path"] = str(json_path)
                    cg_db.update_diario_status(d.url, "analyzed", metadata=d.metadata)
                    typer.echo(f"  ✅ Analyzed: {json_path}")
                else:
                    typer.echo(f"  ❌ Extraction returned no path.")
            except Exception as e:
                typer.echo(f"  ❌ Extraction failed: {e}", err=True)
            finally:
                if temp_pdf and temp_pdf.exists():
                    temp_pdf.unlink()


@app.command()
def score(
    ctx: typer.Context,
    limit: Optional[int] = typer.Option(None, help="Limit items to score"),
    force: bool = typer.Option(False, help="Force re-scoring"),
) -> None:
    """Calculate OpenSkill ratings from analyzed decisions."""
    cg_db = get_cg_db_from_ctx(ctx)
    from openskill_rating import get_openskill_model, create_rating, rate_teams

    diarios = cg_db.get_diarios_by_status("analyzed")
    if not diarios:
        typer.echo("No analyzed items to score.")
        return

    if limit:
        diarios = diarios[:limit]

    model = get_openskill_model()  # Default config

    for d in diarios:
        json_path_str = d.metadata.get("json_path")
        if not json_path_str or not Path(json_path_str).exists():
            typer.echo(
                f"Skipping {d.display_name}: JSON file not found at {json_path_str}"
            )
            continue

        try:
            with open(json_path_str, "r") as f:
                data = json.load(f)
        except Exception as e:
            typer.echo(f"Error reading JSON for {d.display_name}: {e}")
            continue

        decisions = data.get("decisions", [])
        if not decisions:
            typer.echo(f"No decisions in {d.display_name}")
            cg_db.update_diario_status(
                d.url, "scored", metadata=d.metadata
            )  # Mark as scored anyway? Yes.
            continue

        processed_count = 0
        for decision in decisions:
            # Helper to get team ratings
            def get_team_ratings(lawyer_names):
                ratings = []
                ids = []
                for name in lawyer_names:
                    norm_name = normalize_lawyer_name(name)
                    if not norm_name:
                        continue
                    # Unique ID for lawyer? Use normalized name for now
                    adv_id = norm_name

                    db_rating = cg_db.get_rating(adv_id)
                    if db_rating:
                        r = create_rating(
                            model,
                            mu=db_rating["mu"],
                            sigma=db_rating["sigma"],
                            name=adv_id,
                        )
                    else:
                        r = create_rating(model, name=adv_id)  # Default

                    ratings.append(r)
                    ids.append(adv_id)
                return ratings, ids

            team_a_lawyers = decision.get("advogados_polo_ativo", [])
            team_b_lawyers = decision.get("advogados_polo_passivo", [])

            if not team_a_lawyers or not team_b_lawyers:
                # Can't score if one side missing
                continue

            ratings_a, ids_a = get_team_ratings(team_a_lawyers)
            ratings_b, ids_b = get_team_ratings(team_b_lawyers)

            if not ratings_a or not ratings_b:
                continue

            # Determine result
            resultado = decision.get("resultado", "").lower()
            match_result = None
            if "improcedente" in resultado or "negado" in resultado:
                # Polo ativo LOST. Polo passivo WON.
                match_result = "win_b"
            elif "procedente" in resultado or "provido" in resultado:
                # Polo ativo WON.
                if "parcialmente" in resultado:
                    match_result = "partial_a"
                else:
                    match_result = "win_a"
            elif "extinto" in resultado:
                match_result = "draw"  # Or skip?

            if not match_result:
                continue

            # Rate
            new_a, new_b = rate_teams(model, ratings_a, ratings_b, match_result)

            # Update DB
            for r in new_a:
                cg_db.update_rating(r.name, r.mu, r.sigma)
            for r in new_b:
                cg_db.update_rating(r.name, r.mu, r.sigma)

            # Record match
            ratings_antes_a = {
                r.name: {"mu": r.mu, "sigma": r.sigma} for r in ratings_a
            }
            ratings_antes_b = {
                r.name: {"mu": r.mu, "sigma": r.sigma} for r in ratings_b
            }
            ratings_depois_a = {r.name: {"mu": r.mu, "sigma": r.sigma} for r in new_a}
            ratings_depois_b = {r.name: {"mu": r.mu, "sigma": r.sigma} for r in new_b}

            cg_db.add_partida(
                data_partida=decision.get("data", d.data.isoformat()),
                numero_processo=decision.get("numero_processo", "unknown"),
                equipe_a_ids=ids_a,
                equipe_b_ids=ids_b,
                ratings_antes_a=ratings_antes_a,
                ratings_antes_b=ratings_antes_b,
                resultado=match_result,
                ratings_depois_a=ratings_depois_a,
                ratings_depois_b=ratings_depois_b,
            )

            processed_count += 1

        typer.echo(f"Scored {processed_count} decisions in {d.display_name}")
        cg_db.update_diario_status(d.url, "scored", metadata=d.metadata)


@app.command("get-urls")
def get_urls_cmd(
    date: Optional[str] = None,
    latest: bool = False,
    tribunal: str = "tjro",
    to_queue: bool = False,
    as_diario: bool = False,
) -> None:
    typer.echo("get-urls command (stub) NOT YET FULLY REFACTORED.", err=True)


@pipeline_app.command("run")
def pipeline_run(
    date: Optional[str] = typer.Option(
        None, help="Process only a specific YYYY-MM-DD date"
    ),
    max_items: Optional[int] = typer.Option(
        None, help="Limit number of diarios processed"
    ),
    verbose: bool = typer.Option(False, help="Enable verbose logging"),
) -> None:
    """Execute the async pipeline."""
    args = []
    if date:
        args += ["--start-date", date, "--end-date", date]
    if max_items:
        args += ["--max-items", str(max_items)]
    if verbose:
        args.append("--verbose")

    sys_argv_backup = sys.argv
    sys.argv = ["async_diario_pipeline.py"] + args
    try:
        exit_code = asyncio.run(async_pipeline_main())
    finally:
        sys.argv = sys_argv_backup
    raise typer.Exit(exit_code)


@app.command(name="stats")
def stats_cmd(ctx: typer.Context) -> None:
    cg_db = get_cg_db_from_ctx(ctx)
    try:
        with cg_db.db_manager:
            diario_stats = cg_db.get_diario_statistics()
            if not diario_stats or diario_stats.get("total_diarios", 0) == 0:
                typer.echo("📊 No Diarios tracked.")
            else:
                typer.echo(json.dumps(diario_stats, indent=2, default=str))
    except Exception as e:
        typer.echo(f"Error in stats: {e}", err=True)


@app.command(name="config")
def show_config_cmd(ctx: typer.Context) -> None:
    typer.echo(json.dumps(cg_config, indent=2, default=str))




@app.command("diario")
def diario_cmd_group(ctx: typer.Context, action: str = typer.Argument(...)) -> None:
    typer.echo("Diario command (stub) NOT YET FULLY REFACTORED.", err=True)
    if action == "stats":
        ctx.invoke(stats_cmd)


# --- Refactored 'db' command group and its helpers ---
def _db_status(ctx: typer.Context) -> None:
    cg_db = get_cg_db_from_ctx(ctx)
    try:
        with cg_db.db_manager:
            db_info = cg_db.get_db_info()
            typer.echo("💾 Database Status:")
            typer.echo(f"├── Path: {db_info.get('db_path', 'N/A')}")
            actual_db_path = Path(str(db_info.get("db_path")))
            typer.echo(f"├── Exists: {'✅' if actual_db_path.exists() else '❌'}")
            if actual_db_path.exists():
                typer.echo(f"├── Size: {db_info.get('size_mb', 0):.2f} MB")
            typer.echo("├── Table Counts / Info:")
            table_data = db_info.get("tables", {})
            if table_data:
                for table_name, count_or_error in table_data.items():
                    typer.echo(
                        f"│   ├── {table_name.replace('_', ' ').title()}: {count_or_error}"
                    )
            else:
                typer.echo("│   └── No table information available.")
            typer.echo(
                "\n--- For detailed content statistics, run 'causaganha stats' ---"
            )
    except (duckdb.Error, RuntimeError) as e:
        if (
            "no such table" in str(e).lower() or "catalog error" in str(e).lower()
        ):  # common DuckDB errors
            typer.echo(
                f"❌ Database error: {e}. Tables/views might be missing. Run 'db migrate'.",
                err=True,
            )
        else:
            typer.echo(f"❌ Failed to get database status: {e}", err=True)
    except Exception as e_gen:
        typer.echo(f"❌ Unexpected error getting DB status: {e_gen}", err=True)


@app.command("db")
def database_cmd_group(
    ctx: typer.Context,
    action: str = typer.Argument(
        ..., help="Action: migrate, status, backup, reset, healthcheck"
    ),
    force: bool = typer.Option(False, help="Force operation"),
) -> None:
    db_path_cfg = ctx.obj.get(CTX_DB_PATH_CFG, Path(cg_config["database"]["path"]))

    if action == "migrate":
        typer.echo(f"🔄 Running migrations on {db_path_cfg}...")
        try:
            current_manager = ctx.obj.get(CTX_DB_MANAGER)
            if current_manager:
                current_manager.close()
            run_db_migrations(db_path_cfg)
            typer.echo("✅ Migrations completed.")
            new_manager = DatabaseManager(
                db_path_cfg
            )  # Create new manager post-migration
            ctx.obj[CTX_DB_MANAGER] = new_manager
            ctx.obj[CTX_CG_DB] = CausaGanhaDB(new_manager)
        except Exception as e:
            typer.echo(f"❌ Migration failed: {e}", err=True)
            raise typer.Exit(1)
    elif action == "status":
        _db_status(ctx)
    elif action == "healthcheck":
        temp_manager = DatabaseManager(db_path_cfg)
        typer.echo(f"🩺 Health check for {temp_manager.db_path}...")
        if temp_manager.health_check():
            typer.echo("✅ DB health OK.")
        else:
            typer.echo(f"❌ DB health FAILED for {temp_manager.db_path}.", err=True)
            raise typer.Exit(1)
        temp_manager.close()
    elif action == "backup":
        cg_db = get_cg_db_from_ctx(ctx)
        db_actual_path = cg_db.db_manager.db_path
        if not db_actual_path.exists():
            typer.echo(f"❌ DB not found: {db_actual_path}", err=True)
            raise typer.Exit(1)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = db_actual_path.parent / f"{db_actual_path.stem}_backup_{ts}_export"
        typer.echo(f"💿 Exporting DB snapshot to {backup_dir}...")
        try:
            with cg_db.db_manager:
                if cg_db.export_database_snapshot(backup_dir):
                    typer.echo(f"✅ Snapshot to {backup_dir}")
                else:
                    typer.echo("❌ Snapshot export failed.", err=True)
        except Exception as e:
            typer.echo(f"❌ Backup failed: {e}", err=True)
    elif action == "reset":
        if not force and not typer.confirm(
            f"⚠️ DELETE DB at {db_path_cfg} & re-migrate? IRREVERSIBLE!", abort=True
        ):
            return
        typer.echo(f"🗑️ Resetting DB at {db_path_cfg}...")
        try:
            current_manager = ctx.obj.get(CTX_DB_MANAGER)
            if current_manager:
                current_manager.close()
            if db_path_cfg.is_file():
                db_path_cfg.unlink()
            elif db_path_cfg.is_dir():
                import shutil

                shutil.rmtree(db_path_cfg)
            run_db_migrations(db_path_cfg)
            typer.echo("✅ DB Reset & Migrated.")
            new_manager = DatabaseManager(db_path_cfg)  # Create new manager post-reset
            ctx.obj[CTX_DB_MANAGER] = new_manager
            ctx.obj[CTX_CG_DB] = CausaGanhaDB(new_manager)
        except Exception as e:
            typer.echo(f"❌ DB reset failed: {e}", err=True)
            raise typer.Exit(1)
    else:
        typer.echo(f"❌ Unknown 'db' action: {action}", err=True)
        raise typer.Exit(1)


@app.command("backup")
def backup_cmd(ctx: typer.Context) -> None:
    """Create a timestamped backup of the database."""
    db_path_cfg = ctx.obj.get(CTX_DB_PATH_CFG, Path(cg_config["database"]["path"]))
    
    try:
        backup_path = backup_database_before_changes(db_path_cfg)
        typer.echo(f"✅ Database backed up to: {backup_path}")
    except Exception as e:
        typer.echo(f"❌ Backup failed: {e}", err=True)
        raise typer.Exit(1)


@app.command("export")
def export_cmd(ctx: typer.Context) -> None:
    """Export database to parquet format and upload to Internet Archive."""
    db_path_cfg = ctx.obj.get(CTX_DB_PATH_CFG, Path(cg_config["database"]["path"]))
    
    try:
        uploaded_urls = export_and_upload_to_ia(db_path_cfg)
        if uploaded_urls:
            typer.echo(f"✅ Export completed! Uploaded {len(uploaded_urls)} tables:")
            for table_name, url in uploaded_urls.items():
                typer.echo(f"  - {table_name}: {url}")
        else:
            typer.echo("⚠️  No files were uploaded. Check your data and IA credentials.")
    except Exception as e:
        typer.echo(f"❌ Export failed: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    log_level_str = cg_config.get("logging", {}).get("level", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level_str, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
    logger.info(f"CausaGanha CLI starting with log level {log_level_str}...")
    app()
