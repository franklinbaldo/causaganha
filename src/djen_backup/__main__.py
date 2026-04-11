"""CLI entry point for ``djen-backup`` with Typer and Rich."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import NamedTuple

import structlog
import typer
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from djen_backup.credentials import get_ia_s3_auth
from djen_backup.engine import (
    SyncConfig,
    SyncState,
    run_sync,
)


DJEN_DIRECT_URL = "https://comunicaapi.pje.jus.br"
DJEN_PROXY_FALLBACK_URL = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"


class EnvLoadResult(NamedTuple):
    path: Path
    loaded_keys: list[str]


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

    def on_metadata_sync_complete(self, tribunal: str, year: int, _found: int) -> None:
        pass

    def on_gaps_discovered(self, tribunal: str, year: int, count: int) -> None:
        if count > 0:
            task_id = self.progress.add_task(f"[cyan]{tribunal} {year}", total=count, visible=True)
            self.tribunal_tasks[f"{tribunal}-{year}"] = task_id
        else:
            self.progress.console.log(f"[green][OK][/green] {tribunal} {year} is up to date.")

    def on_item_start(self, tribunal: str, d: date) -> None:
        pass

    def on_item_complete(self, tribunal: str, d: date, status: str, url: str | None = None) -> None:
        # Log successful uploads/hits with URL
        if status == "hit" and url:
            self.progress.console.log(
                f"[green][OK][/green] {tribunal} {d.isoformat()} [dim]({url})[/dim]"
            )

        # Find the task for this tribunal-year
        task_key = f"{tribunal}-{d.year}"
        if task_key in self.tribunal_tasks:
            self.progress.advance(self.tribunal_tasks[task_key])
            self.progress.advance(self.main_task)

    def on_retry(
        self,
        tribunal: str,
        d: date,
        attempt: int,
        status: int,
        wait_s: float,
        body: str | None = None,
    ) -> None:
        msg = (
            f"[bold yellow][Retry {attempt}][/bold yellow] for {tribunal} {d.isoformat()} "
            f"(Status: {status}). Waiting {wait_s:.1f}s..."
        )
        if body:
            msg += f" [dim]Reason: {body}[/dim]"
        self.progress.console.log(msg)

    def on_periodic_sync_start(self) -> None:
        self.progress.console.log(
            "[yellow][Sync][/yellow] Periodic sync to Internet Archive starting..."
        )

    def on_periodic_sync_complete(self) -> None:
        self.progress.console.log("[green][OK][/green] Periodic sync complete.")

    def on_batch_upload_start(self, item_id: str, count: int) -> None:
        self.progress.console.log(f"[bold blue][Upload][/bold blue] {item_id} ({count} files)")

    def on_batch_upload_complete(self, item_id: str, count: int) -> None:
        self.progress.console.log(
            f"[bold green][OK][/bold green] Batch upload complete: {item_id} ({count} files)"
        )


# ── CLI Helpers ─────────────────────────────────────────────────────


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _load_local_env(path: Path = Path(".env")) -> EnvLoadResult | None:
    if not path.exists():
        return None

    loaded_keys: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or key in os.environ:
            continue
        os.environ[key] = value
        loaded_keys.append(key)

    return EnvLoadResult(path=path.resolve(), loaded_keys=loaded_keys)


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_djen_url(*, use_proxy: bool) -> str:
    if use_proxy:
        return os.environ.get("DJEN_PROXY_URL", "").strip() or DJEN_PROXY_FALLBACK_URL
    return os.environ.get("DJEN_DIRECT_URL", "").strip() or DJEN_DIRECT_URL


def _resolve_ia_auth(*, dry_run: bool) -> str:
    try:
        return get_ia_s3_auth()
    except RuntimeError as exc:
        if dry_run:
            return "LOW dry-run:dry-run"
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


def _show_env_hint(env_result: EnvLoadResult | None) -> None:
    if not env_result:
        return
    if env_result.loaded_keys:
        joined = ", ".join(env_result.loaded_keys)
        console.print(f"[dim]Loaded environment from {env_result.path} ({joined})[/dim]")
    else:
        console.print(f"[dim]Using existing environment; {env_result.path} was not applied[/dim]")


def _show_run_summary(
    exit_code: int, *, dry_run: bool, tribunal: str | None, max_items: int
) -> None:
    title = "Run Complete" if exit_code == 0 else "Run Finished With Errors"
    border = "green" if exit_code == 0 else "red"
    rows = Table.grid(padding=(0, 2))
    rows.add_column(style="bold cyan")
    rows.add_column()
    rows.add_row("Status:", "[green]OK[/green]" if exit_code == 0 else "[red]Error[/red]")
    rows.add_row("Mode:", "Dry run" if dry_run else "Live upload")
    rows.add_row("Tribunal:", tribunal or "All")
    rows.add_row("Item Limit:", str(max_items) if max_items else "Unlimited")
    if exit_code == 0 and not dry_run:
        rows.add_row(
            "Note:", "Completed cleanly. Zero uploads can still mean nothing new was found."
        )
    elif exit_code == 0:
        rows.add_row("Note:", "Dry run completed cleanly.")
    else:
        rows.add_row("Note:", "See warnings above for the failing stage.")
    console.print(Panel(rows, title=f"[bold white]{title}[/bold white]", border_style=border))


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
def main(  # noqa: PLR0913
    ctx: typer.Context,
    start_date: str | None = typer.Option(
        None, "--start-date", help="Oldest date to scan (YYYY-MM-DD)."
    ),
    end_date: str | None = typer.Option(
        None, "--end-date", help="Newest date to scan (YYYY-MM-DD)."
    ),
    tribunal: str | None = typer.Option(
        None, "--tribunal", help="Process a single tribunal (e.g. TJSP)."
    ),
    deadline_minutes: int = typer.Option(45, "--deadline-minutes", help="Time budget in minutes."),
    max_items: int = typer.Option(
        0, "--max-items", help="Max dates per tribunal per run (0 = unlimited)."
    ),
    workers: int = typer.Option(4, "--workers", help="Parallel workers."),
    backfill_state_file: Path | None = typer.Option(
        None, "--backfill-state-file", help="Path to backfill progress JSON."
    ),
    state_file: Path | None = typer.Option(
        None, "--state-file", help="Path to IA state cache JSON (obsolete)."
    ),
    *,
    dry_run: bool = typer.Option(False, "--dry-run", help="Log actions without uploading."),
    skip_absent_markers: bool = typer.Option(
        False, "--skip-absent-markers", help="Skip uploading absent markers."
    ),
    publish_live_status: bool = typer.Option(
        False, "--publish-live-status", help="Publish live status to IA."
    ),
    skip_if_mostly_complete: bool = typer.Option(
        False,
        "--skip-if-mostly-complete",
        help="Skip collection if today is already mostly complete.",
    ),
    use_proxy: bool = typer.Option(
        False,
        "--use-proxy",
        help="Use the Cloud Run DJEN proxy. Default is direct access.",
    ),
):
    """Main backup and sync command."""
    if ctx.invoked_subcommand:
        return
    env_result = _load_local_env()
    show_banner()
    _show_env_hint(env_result)

    today = datetime.now(tz=UTC).date()
    resolved_end = _parse_date(end_date) if end_date else today - timedelta(days=1)
    resolved_start = _parse_date(start_date) if start_date else date(2020, 1, 1)
    resolved_use_proxy = use_proxy or _env_truthy("DJEN_USE_PROXY")
    resolved_djen_url = _resolve_djen_url(use_proxy=resolved_use_proxy)

    resolved_state_file = backfill_state_file or state_file

    # Show config panel
    config_table = Table.grid(padding=(0, 2))
    config_table.add_column(style="bold cyan")
    config_table.add_column()
    config_table.add_row("End Date:", resolved_end.isoformat())
    config_table.add_row(
        "Start Date:", resolved_start.isoformat() if resolved_start else "2013-01-01 (Auto)"
    )
    config_table.add_row("Tribunal:", tribunal or "All")
    config_table.add_row("Deadline:", f"{deadline_minutes} min")
    config_table.add_row("Max Items:", str(max_items) if max_items else "Unlimited")
    config_table.add_row("Workers:", str(workers))
    config_table.add_row("Dry Run:", "[yellow]Yes[/yellow]" if dry_run else "[green]No[/green]")
    config_table.add_row("DJEN Mode:", "Proxy" if resolved_use_proxy else "Direct")
    config_table.add_row("DJEN URL:", resolved_djen_url)

    console.print(
        Panel(config_table, title="[bold white]Run Configuration[/bold white]", border_style="blue")
    )

    # Prepare Rich components
    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        expand=True,
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
        djen_proxy_url=resolved_djen_url,
        ia_auth=_resolve_ia_auth(dry_run=dry_run),
        dry_run=dry_run,
        skip_absent_markers=skip_absent_markers,
        publish_live_status=publish_live_status,
        skip_if_mostly_complete=skip_if_mostly_complete,
        observer=observer,
    )

    with Live(Group(progress), console=console, refresh_per_second=4):
        exit_code = asyncio.run(run_sync(config))

    _show_run_summary(
        exit_code,
        dry_run=dry_run,
        tribunal=tribunal,
        max_items=max_items,
    )
    raise typer.Exit(code=exit_code)


@app.command()
def reset(
    tribunal: str | None = typer.Option(None, "--tribunal", help="Tribunal code to reset."),
    *,
    reset_all: bool = typer.Option(False, "--all", help="Reset all stopped tribunals."),
    backfill_state_file: Path | None = typer.Option(
        None, "--backfill-state-file", exists=True, help="Path to state JSON."
    ),
    set_cursor: str | None = typer.Option(
        None, "--set-cursor", help="Set the cursor to this date (YYYY-MM-DD)."
    ),
):
    """Reset stopped tribunal(s) for re-scanning."""
    import json

    if not tribunal and not reset_all:
        console.print("[bold red]Error:[/bold red] provide --tribunal CODE or --all")
        raise typer.Exit(code=1)

    if not backfill_state_file or not backfill_state_file.exists():
        console.print("[bold red]Error:[/bold red] state file not found.")
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
                    console.print(
                        f"[green]Reset {tribunal} and set cursor to {target_date}[/green]"
                    )
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
