"""CLI entry point for ``djen-backup``."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import click
import structlog

from djen_backup.engine import (
    SyncConfig,
    SyncState,
    run_sync,
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


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _resolve_proxy_url() -> str:
    return (
        os.environ.get("DJEN_PROXY_URL", "").strip() or "https://djen-proxy-mhgmawcn3a-rj.a.run.app"
    )


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
    help="Path to IA state cache JSON (obsolete, now used for backfill progress fallback).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Log actions without uploading.",
)
@click.option(
    "--skip-absent-markers",
    is_flag=True,
    default=False,
    help="Skip uploading absent markers to avoid IA spam detection.",
)
@click.option(
    "--publish-live-status",
    is_flag=True,
    default=False,
    help="Publish live status JSON to the causaganha-live-status Internet Archive item.",
)
@click.option(
    "--skip-if-mostly-complete",
    is_flag=True,
    default=False,
    help="Skip execution if target date has > 80 successful collections.",
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
    publish_live_status: bool,
    skip_if_mostly_complete: bool,
    dry_run: bool,
    skip_absent_markers: bool,
) -> None:
    """Back up DJEN judicial communications to the Internet Archive."""
    if ctx.invoked_subcommand is not None:
        return

    today = datetime.now(tz=UTC).date()
    resolved_end = _parse_date(end_date) if end_date else today - timedelta(days=1)
    resolved_start = _parse_date(start_date) if start_date else None
    
    # Use backfill_state_file if provided, else fall back to state_file for backward compat
    resolved_state_file = backfill_state_file or state_file

    config = SyncConfig(
        start_date=resolved_end,
        lower_bound=resolved_start,
        tribunal=tribunal,
        deadline_minutes=deadline_minutes,
        max_items=max_items,
        workers=workers,
        state_file=resolved_state_file,
        djen_proxy_url=_resolve_proxy_url(),
        ia_auth=_resolve_ia_auth(dry_run=dry_run),
        dry_run=dry_run,
        skip_absent_markers=skip_absent_markers,
        publish_live_status=publish_live_status,
    )

    sys.exit(asyncio.run(run_sync(config)))


@main.command()
@click.option("--tribunal", type=click.STRING, help="Tribunal code to reset.")
@click.option("--all", "reset_all", is_flag=True, help="Reset all stopped tribunals.")
@click.option(
    "--backfill-state-file",
    type=click.Path(path_type=Path, exists=True),
    help="Path to state JSON.",
)
@click.option(
    "--set-cursor",
    type=click.STRING,
    help="Set the cursor to this date (YYYY-MM-DD) instead of just unstopping.",
)
def reset(
    tribunal: str | None,
    reset_all: bool,
    backfill_state_file: Path | None,
    set_cursor: str | None,
) -> None:
    """Reset stopped tribunal(s) for re-scanning."""
    import json
    
    if not tribunal and not reset_all:
        click.echo("Error: provide --tribunal CODE or --all", err=True)
        sys.exit(1)

    if not backfill_state_file or not backfill_state_file.exists():
        click.echo("Error: state file not found.", err=True)
        sys.exit(1)

    state_data = json.loads(backfill_state_file.read_text())
    bstate = SyncState.from_dict(state_data)

    async def _reset() -> int:
        count = 0
        target_cursor = None
        if set_cursor:
            target_cursor = date.fromisoformat(set_cursor)

        if tribunal:
            if target_cursor:
                # set_cursor logic would need to be re-implemented in SyncState if needed
                # For now let's just ensure_cursor_at_least is available
                if await bstate.ensure_cursor_at_least(tribunal, target_cursor):
                    click.echo(f"Reset {tribunal} and set cursor to at least {target_cursor.isoformat()}")
                    count = 1
            else:
                # Simplified reset
                prog = bstate.get_all_progress().get(tribunal)
                if prog:
                    prog.stopped = False
                    prog.empty_streak = 0
                    click.echo(f"Reset {tribunal}")
                    count = 1
        else:
            for code, prog in bstate.get_all_progress().items():
                if prog.stopped:
                    prog.stopped = False
                    prog.empty_streak = 0
                    click.echo(f"Reset {code}")
                    count += 1
        return count

    count = asyncio.run(_reset())
    if count > 0:
        backfill_state_file.write_text(json.dumps(bstate.to_dict(), indent=2))
        click.echo(f"\n{count} tribunal(s) reset.")
    else:
        click.echo("Nothing to reset.")


if __name__ == "__main__":
    main()
