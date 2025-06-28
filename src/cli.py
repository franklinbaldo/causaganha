"""CausaGanha CLI - Modern command-line interface for judicial document processing."""

import typer
from typing import Optional
from pathlib import Path
from urllib.parse import urlparse
import re
from datetime import datetime
import json
import logging
import duckdb
from ia_database_sync import IADatabaseSync

from database import DatabaseManager, CausaGanhaDB, run_db_migrations
from config import load_config

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="causaganha",
    help="Judicial document processing pipeline with OpenSkill rating system.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)

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


def extract_tribunal_from_url(url: str) -> str:
    return urlparse(url).netloc.lower()


def validate_tribunal_url(url: str) -> bool:
    return urlparse(url).netloc.lower().endswith(".jus.br")


def extract_date_from_url(url: str) -> Optional[str]:
    date_patterns = [
        r"diario(?:jus)?(?:tj)?(\d{8})",
        r"(?:data=|date=|dt=)(\d{8})",
        r"(\d{4})[/_-]?(\d{2})[/_-]?(\d{2})",
        r"(\d{2})[/_-]?(\d{2})[/_-]?(\d{4})",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            groups = match.groups()
            try:
                if len(groups) == 3:
                    year, month, day = (
                        (int(groups[0]), int(groups[1]), int(groups[2]))
                        if len(groups[0]) == 4
                        else (int(groups[2]), int(groups[1]), int(groups[0]))
                    )
                    return datetime(year, month, day).strftime("%Y-%m-%d")
                elif len(groups) == 1 and len(groups[0]) == 8 and groups[0].isdigit():
                    return datetime.strptime(groups[0], "%Y%m%d").strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


# --- Stubs for commands not yet refactored ---
@app.command()
def queue(url: Optional[str] = None, from_csv: Optional[Path] = None) -> None:
    typer.echo("Queue command (stub) NOT YET FULLY REFACTORED.", err=True)
    global db  # Uses old global db
    if not url and not from_csv:
        typer.echo("URL or CSV needed.", err=True)
        raise typer.Exit(1)
    try:
        with db.db_manager as mgr:  # Old db uses a manager
            mgr.get_connection().execute(
                "CREATE TABLE IF NOT EXISTS job_queue (url TEXT UNIQUE, status TEXT)"
            )
            typer.echo("Simplified queue logic ran using old 'db' instance.")
    except Exception as e:
        typer.echo(f"Error in stubbed queue: {e}", err=True)


@app.command()
def archive(limit: Optional[int] = None, force: bool = False) -> None:
    typer.echo("Archive command (stub) NOT YET FULLY REFACTORED.", err=True)


@app.command()
def analyze(limit: Optional[int] = None, force: bool = False) -> None:
    typer.echo("Analyze command (stub) NOT YET FULLY REFACTORED.", err=True)


@app.command()
def score(force: bool = False) -> None:
    typer.echo("Score command (stub) NOT YET FULLY REFACTORED.", err=True)


@app.command("get-urls")
def get_urls_cmd(
    date: Optional[str] = None,
    latest: bool = False,
    tribunal: str = "tjro",
    to_queue: bool = False,
    as_diario: bool = False,
) -> None:
    typer.echo("get-urls command (stub) NOT YET FULLY REFACTORED.", err=True)


@app.command()
def pipeline(
    from_csv: Optional[Path] = None,
    stages: Optional[str] = None,
    stop_on_error: bool = False,
    limit: Optional[int] = None,
) -> None:
    typer.echo("Pipeline command (stub) NOT YET FULLY REFACTORED.", err=True)


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


@app.command("archive-status")
def archive_status_cmd(verbose: bool = False) -> None:
    """Display Internet Archive sync status."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    sync = IADatabaseSync()
    status = sync.sync_status()
    typer.echo(json.dumps(status, indent=2, default=str))


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
