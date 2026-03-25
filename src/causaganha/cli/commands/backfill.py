"""CLI command module for CausaGanha backfill."""

import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import typer
import structlog

from djen_backup.backfill import (
    BackfillConfig,
    load_backfill_state,
    run_backfill,
    save_backfill_state,
)
from djen_backup.credentials import get_ia_s3_auth

logger = structlog.get_logger()

# We use the proxy URL for DJEN API
DEFAULT_PROXY_URL = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"

app = typer.Typer(
    help="Manage the DJEN backfill pipeline and Internet Archive uploads.",
    no_args_is_help=True,
)

def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)

def _resolve_proxy_url() -> str:
    return os.environ.get("DJEN_PROXY_URL", "").strip() or DEFAULT_PROXY_URL

def _resolve_ia_auth(*, dry_run: bool) -> str:
    try:
        return get_ia_s3_auth()
    except RuntimeError as exc:
        if dry_run:
            return "LOW dry-run:dry-run"
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command()
def run(
    start_date: str | None = typer.Option(
        None,
        help="Oldest date to scan (YYYY-MM-DD). Default: no lower bound.",
    ),
    end_date: str | None = typer.Option(
        None,
        help="Newest date to scan (YYYY-MM-DD). Default: yesterday.",
    ),
    tribunal: str | None = typer.Option(
        None,
        help="Process a single tribunal (e.g. TJSP).",
    ),
    deadline_minutes: int = typer.Option(
        45,
        help="Time budget in minutes.",
    ),
    max_items: int = typer.Option(
        0,
        help="Max dates per tribunal per run (0 = unlimited).",
    ),
    workers: int = typer.Option(
        1,
        help="Parallel workers.",
    ),
    backfill_state_file: Path = typer.Option(
        Path("data/backfill-state.json"),
        help="Path to backfill progress JSON.",
    ),
    state_file: Path = typer.Option(
        Path("data/ia-state.json"),
        help="Path to IA state cache JSON.",
    ),
    dry_run: bool = typer.Option(
        False,
        help="Log actions without uploading.",
    ),
    skip_absent_markers: bool = typer.Option(
        False,
        help=(
            "Skip uploading absent markers to IA when DJEN returns 404. "
            "The empty streak still increments (60-day stop rule works). "
            "Use for historical backfill to avoid IA 503 rate-limit floods."
        ),
    ),
) -> None:
    """Back up DJEN judicial communications to the Internet Archive."""
    import asyncio

    today = datetime.now(tz=UTC).date()
    resolved_end = _parse_date(end_date) if end_date else today - timedelta(days=1)
    resolved_start = _parse_date(start_date) if start_date else None

    config = BackfillConfig(
        start_date=resolved_end,
        lower_bound=resolved_start,
        tribunal=tribunal,
        deadline_minutes=deadline_minutes,
        max_items=max_items,
        workers=workers,
        backfill_state_file=backfill_state_file,
        state_file=state_file,
        djen_proxy_url=_resolve_proxy_url(),
        ia_auth=_resolve_ia_auth(dry_run=dry_run),
        dry_run=dry_run,
        skip_absent_markers=skip_absent_markers,
    )

    lower_str = config.lower_bound.isoformat() if config.lower_bound else "none"
    logger.info(
        "starting_backup",
        end=config.start_date.isoformat(),
        lower_bound=lower_str,
        tribunal=config.tribunal or "all",
        workers=config.workers,
        deadline_min=config.deadline_minutes,
        dry_run=config.dry_run,
    )

    exit_code = asyncio.run(run_backfill(config))
    sys.exit(exit_code)


@app.command()
def status(
    backfill_state_file: Path = typer.Option(
        Path("data/backfill-state.json"),
        help="Path to backfill progress JSON.",
    ),
) -> None:
    """Show per-tribunal backfill progress."""
    bstate = load_backfill_state(backfill_state_file)
    progress = bstate.get_all_progress()

    if not progress:
        typer.echo("No backfill state found.")
        return

    running = sum(1 for p in progress.values() if not p.stopped)
    stopped = sum(1 for p in progress.values() if p.stopped)
    typer.echo(f"Tribunals: {len(progress)} total, {running} running, {stopped} stopped\n")

    for code in sorted(progress):
        prog = progress[code]
        flag = "STOPPED" if prog.stopped else "running"
        hit_str = prog.last_hit_date.isoformat() if prog.last_hit_date else "never"
        typer.echo(
            f"  {code:12s}  {flag:8s}  cursor={prog.cursor_date.isoformat()}"
            f"  streak={prog.empty_streak:3d}  last_hit={hit_str}"
        )


@app.command()
def reset(
    tribunal: str | None = typer.Option(
        None,
        help="Reset a specific tribunal. Omit for --all.",
    ),
    all: bool = typer.Option(
        False,
        "--all",
        help="Reset all stopped tribunals.",
    ),
    backfill_state_file: Path = typer.Option(
        Path("data/backfill-state.json"),
        help="Path to backfill progress JSON.",
    ),
) -> None:
    """Reset stopped tribunal(s) for re-scanning."""
    import asyncio

    if not tribunal and not all:
        typer.echo("Error: provide --tribunal CODE or --all", err=True)
        raise typer.Exit(code=1)

    bstate = load_backfill_state(backfill_state_file)
    progress = bstate.get_all_progress()

    async def _reset() -> int:
        count = 0
        if tribunal:
            if await bstate.reset_tribunal(tribunal):
                typer.echo(f"Reset {tribunal}")
                count = 1
            else:
                typer.echo(f"Tribunal {tribunal} not found in state.", err=True)
        else:
            for code, prog in progress.items():
                if prog.stopped:
                    await bstate.reset_tribunal(code)
                    typer.echo(f"Reset {code}")
                    count += 1
        return count

    count = asyncio.run(_reset())
    if count > 0:
        save_backfill_state(bstate, backfill_state_file)
        typer.echo(f"\n{count} tribunal(s) reset.")
    else:
        typer.echo("Nothing to reset.")
