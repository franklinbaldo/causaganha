"""CLI entry point for ``djen-backup``."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import click
import structlog

from djen_backup.backfill import (
    BackfillConfig,
    load_backfill_state,
    run_backfill,
    save_backfill_state,
)
from djen_backup.credentials import get_ia_s3_auth


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

# Stable Cloud Run URL for the DJEN proxy service.
# Override via the DJEN_PROXY_URL environment variable if redeployed.
DEFAULT_PROXY_URL = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _resolve_proxy_url() -> str:
    return os.environ.get("DJEN_PROXY_URL", "").strip() or DEFAULT_PROXY_URL


def _resolve_ia_auth(*, dry_run: bool) -> str:
    try:
        return get_ia_s3_auth()
    except RuntimeError as exc:
        if dry_run:
            return "LOW dry-run:dry-run"
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


# ── CLI group ────────────────────────────────────────────────────────


@click.group(invoke_without_command=True)
@click.option(
    "--start-date",
    type=click.STRING,
    default=None,
    help="Oldest date to scan (YYYY-MM-DD). Default: no lower bound.",
)
@click.option(
    "--end-date",
    type=click.STRING,
    default=None,
    help="Newest date to scan (YYYY-MM-DD). Default: yesterday.",
)
@click.option(
    "--tribunal",
    type=click.STRING,
    default=None,
    help="Process a single tribunal (e.g. TJSP).",
)
@click.option(
    "--deadline-minutes",
    type=int,
    default=45,
    show_default=True,
    help="Time budget in minutes.",
)
@click.option(
    "--max-items",
    type=int,
    default=0,
    help="Max dates per tribunal per run (0 = unlimited).",
)
@click.option(
    "--workers",
    type=int,
    default=1,
    show_default=True,
    help="Parallel workers.",
)
@click.option(
    "--backfill-state-file",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to backfill progress JSON.",
)
@click.option(
    "--state-file",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to IA state cache JSON.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Log actions without uploading.",
)

@click.pass_context
def main(  # noqa: PLR0913
    ctx: click.Context,
    start_date: str | None,
    end_date: str | None,
    tribunal: str | None,
    deadline_minutes: int,
    max_items: int,
    workers: int,
    backfill_state_file: Path | None,
    state_file: Path | None,
    *,
    dry_run: bool,
) -> None:
    """Back up DJEN judicial communications to the Internet Archive.

    Scans backward from --end-date per tribunal, stopping each after
    60 consecutive authoritative empty days.  Progress is persisted
    across runs via --backfill-state-file.
    """
    if ctx.invoked_subcommand is not None:
        return

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
    )

    log = structlog.get_logger()
    lower_str = config.lower_bound.isoformat() if config.lower_bound else "none"
    log.info(
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


# ── status (show backfill progress) ──────────────────────────────────


@main.command()
@click.option(
    "--backfill-state-file",
    type=click.Path(path_type=Path),
    required=True,
    help="Path to backfill progress JSON.",
)
def status(backfill_state_file: Path) -> None:
    """Show per-tribunal backfill progress."""
    bstate = load_backfill_state(backfill_state_file)
    progress = bstate.get_all_progress()

    if not progress:
        click.echo("No backfill state found.")
        return

    running = sum(1 for p in progress.values() if not p.stopped)
    stopped = sum(1 for p in progress.values() if p.stopped)
    click.echo(f"Tribunals: {len(progress)} total, {running} running, {stopped} stopped\n")

    for code in sorted(progress):
        prog = progress[code]
        flag = "STOPPED" if prog.stopped else "running"
        hit_str = prog.last_hit_date.isoformat() if prog.last_hit_date else "never"
        click.echo(
            f"  {code:12s}  {flag:8s}  cursor={prog.cursor_date.isoformat()}"
            f"  streak={prog.empty_streak:3d}  last_hit={hit_str}"
        )


# ── reset (re-enable stopped tribunals) ──────────────────────────────


@main.command()
@click.option(
    "--backfill-state-file",
    type=click.Path(path_type=Path),
    required=True,
    help="Path to backfill progress JSON.",
)
@click.option(
    "--tribunal",
    type=click.STRING,
    default=None,
    help="Reset a specific tribunal. Omit for --all.",
)
@click.option(
    "--all",
    "reset_all",
    is_flag=True,
    default=False,
    help="Reset all stopped tribunals.",
)
def reset(
    backfill_state_file: Path,
    tribunal: str | None,
    *,
    reset_all: bool,
) -> None:
    """Reset stopped tribunal(s) for re-scanning."""
    if not tribunal and not reset_all:
        click.echo("Error: provide --tribunal CODE or --all", err=True)
        sys.exit(1)

    bstate = load_backfill_state(backfill_state_file)
    progress = bstate.get_all_progress()

    async def _reset() -> int:
        count = 0
        if tribunal:
            if await bstate.reset_tribunal(tribunal):
                click.echo(f"Reset {tribunal}")
                count = 1
            else:
                click.echo(f"Tribunal {tribunal} not found in state.", err=True)
        else:
            for code, prog in progress.items():
                if prog.stopped:
                    await bstate.reset_tribunal(code)
                    click.echo(f"Reset {code}")
                    count += 1
        return count

    count = asyncio.run(_reset())
    if count > 0:
        save_backfill_state(bstate, backfill_state_file)
        click.echo(f"\n{count} tribunal(s) reset.")
    else:
        click.echo("Nothing to reset.")


if __name__ == "__main__":
    main()
