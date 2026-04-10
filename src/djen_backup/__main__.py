"""CLI entry point for ``djen-backup`` with Typer and Rich."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Optional

import typer
import structlog
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    TaskID,
)
from rich.live import Live
from rich.console import Group
from rich.logging import RichHandler

from djen_backup.engine import (
    SyncConfig,
    SyncState,
    SyncObserver,
    run_sync,
)
from djen_backup.credentials import get_ia_s3_auth

# ── Setup ───────────────────────────────────────────────────────────

app = typer.Typer(
    help="Back up DJEN judicial communications to the Internet Archive.",
    no_args_is_help=False,
)
console = Console()

# Configure structlog to use Rich for pretty logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

# ── Rich Observer ───────────────────────────────────────────────────

class RichSyncObserver:
    def __init__(self, progress: Progress):
        self.progress = progress
        self.tribunal_tasks: dict[str, TaskID] = {}
        self.main_task = self.progress.add_task("[bold blue]Overall Progress", total=None)

    def on_metadata_sync_start(self, tribunal: str, year: int) -> None:
        self.progress.console.log(f"[dim]Syncing metadata for {tribunal} ({year})...[/dim]")

    def on_metadata_sync_complete(self, tribunal: str, year: int, found: int) -> None:
        pass

    def on_gaps_discovered(self, tribunal: str, year: int, count: int) -> None:
        if count > 0:
            task_id = self.progress.add_task(
                f"[cyan]{tribunal} {year}", 
                total=count,
                visible=True
            )
            self.tribunal_tasks[f"{tribunal}-{year}"] = task_id
        else:
            self.progress.console.log(f"[green]✓ {tribunal} {year} is up to date.[/green]")

    def on_item_start(self, tribunal: str, d: date) -> None:
        pass

    def on_item_complete(self, tribunal: str, d: date, status: str) -> None:
        # Find the task for this tribunal-year
        task_key = f"{tribunal}-{d.year}"
        if task_key in self.tribunal_tasks:
            self.progress.advance(self.tribunal_tasks[task_key])
            self.progress.advance(self.main_task)

    def on_periodic_sync_start(self) -> None:
        self.progress.console.log("[yellow]⟳ Periodic sync to Internet Archive starting...[/yellow]")

    def on_periodic_sync_complete(self) -> None:
        self.progress.console.log("[green]✓ Periodic sync complete.[/green]")


# ── CLI Helpers ─────────────────────────────────────────────────────

def _parse_date(value: str) -> date:
    return date.fromisoformat(value)

def _resolve_proxy_url() -> str:
    return (
        os.environ.get("DJEN_PROXY_URL", "").strip() or "https://djen-proxy-mhgmawcn3a-rj.a.run.app"
    )

def _resolve_ia_auth(dry_run: bool) -> str:
    try:
        return get_ia_s3_auth()
    except RuntimeError as exc:
        if dry_run:
            return "LOW dry-run:dry-run"
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)

def show_banner():
    banner = r"""
[bold green]
   ______                               ______            __            
  / ____/___ ___  __________ __________ _/ ____/___ _____  / /_  ____ _
 / /   / __ `/ / / / ___/ __ `/ ___/ __ `/ / __/ __ `/ __ \/ __ \/ __ `/
/ /___/ /_/ / /_/ (__  ) /_/ / /  / /_/ / /_/ / /_/ / / / / / / / /_/ / 
\____/\__,_/\__,_/____/\__,_/_/   \__,_/\____/\__,_/ / /_/_/ /_/\__,_/  
[/bold green]
[bold white]DJEN Backup Engine v2.0 - Unified Sync Module[/bold white]
"""
    console.print(Panel(banner, border_style="green"))

# ── Commands ────────────────────────────────────────────────────────

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    start_date: Optional[str] = typer.Option(None, "--start-date", help="Oldest date to scan (YYYY-MM-DD)."),
    end_date: Optional[str] = typer.Option(None, "--end-date", help="Newest date to scan (YYYY-MM-DD)."),
    tribunal: Optional[str] = typer.Option(None, "--tribunal", help="Process a single tribunal (e.g. TJSP)."),
    deadline_minutes: int = typer.Option(45, "--deadline-minutes", help="Time budget in minutes."),
    max_items: int = typer.Option(0, "--max-items", help="Max dates per tribunal per run (0 = unlimited)."),
    workers: int = typer.Option(1, "--workers", help="Parallel workers."),
    backfill_state_file: Optional[Path] = typer.Option(None, "--backfill-state-file", help="Path to backfill progress JSON."),
    state_file: Optional[Path] = typer.Option(None, "--state-file", help="Path to IA state cache JSON (obsolete)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Log actions without uploading."),
    skip_absent_markers: bool = typer.Option(False, "--skip-absent-markers", help="Skip uploading absent markers."),
    publish_live_status: bool = typer.Option(False, "--publish-live-status", help="Publish live status to IA."),
):
    """Main backup and sync command."""
    if ctx.invoked_subcommand:
        return
    show_banner()

    today = datetime.now(tz=UTC).date()
    resolved_end = _parse_date(end_date) if end_date else today - timedelta(days=1)
    resolved_start = _parse_date(start_date) if start_date else None
    
    resolved_state_file = backfill_state_file or state_file

    # Show config panel
    config_table = Table.grid(padding=(0, 2))
    config_table.add_column(style="bold cyan")
    config_table.add_column()
    config_table.add_row("End Date:", resolved_end.isoformat())
    config_table.add_row("Start Date:", resolved_start.isoformat() if resolved_start else "2013-01-01 (Auto)")
    config_table.add_row("Tribunal:", tribunal or "All")
    config_table.add_row("Workers:", str(workers))
    config_table.add_row("Dry Run:", "[yellow]Yes[/yellow]" if dry_run else "[green]No[/green]")
    
    console.print(Panel(config_table, title="[bold white]Run Configuration[/bold white]", border_style="blue"))

    # Prepare Rich components
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        expand=True
    )
    
    observer = RichSyncObserver(progress)

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
        observer=observer
    )

    with Live(Group(progress), console=console, refresh_per_second=4):
        exit_code = asyncio.run(run_sync(config))
    
    raise typer.Exit(code=exit_code)


@app.command()
def reset(
    tribunal: Optional[str] = typer.Option(None, "--tribunal", help="Tribunal code to reset."),
    reset_all: bool = typer.Option(False, "--all", help="Reset all stopped tribunals."),
    backfill_state_file: Path = typer.Option(..., "--backfill-state-file", exists=True, help="Path to state JSON."),
    set_cursor: Optional[str] = typer.Option(None, "--set-cursor", help="Set the cursor to this date (YYYY-MM-DD)."),
):
    """Reset stopped tribunal(s) for re-scanning."""
    import json
    
    if not tribunal and not reset_all:
        console.print("[bold red]Error:[/bold red] provide --tribunal CODE or --all")
        raise typer.Exit(code=1)

    state_data = json.loads(backfill_state_file.read_text())
    bstate = SyncState.from_dict(state_data)

    async def _reset() -> int:
        count = 0
        if tribunal:
            prog = bstate.get_all_progress().get(tribunal)
            if prog:
                if set_cursor:
                    target_date = date.fromisoformat(set_cursor)
                    await bstate.ensure_cursor_at_least(tribunal, target_date)
                    console.print(f"[green]Reset {tribunal} and set cursor to {target_date}[/green]")
                else:
                    prog.stopped = False
                    prog.empty_streak = 0
                    console.print(f"[green]Reset {tribunal}[/green]")
                count = 1
        elif reset_all:
            for code, prog in bstate.get_all_progress().items():
                if prog.stopped:
                    prog.stopped = False
                    prog.empty_streak = 0
                    console.print(f"[green]Reset {code}[/green]")
                    count += 1
        return count

    count = asyncio.run(_reset())
    if count > 0:
        backfill_state_file.write_text(json.dumps(bstate.to_dict(), indent=2))
        console.print(f"\n[bold green]{count} tribunal(s) reset.[/bold green]")
    else:
        console.print("[yellow]Nothing to reset.[/yellow]")


if __name__ == "__main__":
    app()
