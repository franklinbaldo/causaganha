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
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from djen_backup.credentials import get_ia_s3_auth
from djen_backup.engine import SyncConfig, load_djen_safe_concurrency, run_sync
from djen_backup.manifest import ManifestCounts, SyncManifest


DJEN_DIRECT_URL = "https://comunicaapi.pje.jus.br"
DJEN_PROXY_FALLBACK_URL = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"

# Default worker count — discovered via scripts/stress_test_djen.py
DEFAULT_WORKERS = load_djen_safe_concurrency()


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


class RichManifestObserver:
    """Rich-based observer for the manifest-driven sync engine."""

    def __init__(self, progress: Progress) -> None:
        self.progress = progress
        self.main_task = self.progress.add_task("[bold blue]Initializing...", total=None)
        self._subtasks: dict[str, int] = {}  # name -> task_id
        self._start_time: float | None = None
        self._start_uploaded: int = 0
        self._start_absent: int = 0
        self._start_unknown: int = 0

    def on_phase(self, phase: str) -> None:
        self.progress.console.log(f"[bold cyan]Phase:[/bold cyan] {phase}")

    @staticmethod
    def _vel(delta: int, elapsed_min: float) -> str:
        if elapsed_min < 0.1:
            return ""
        v = int(delta / elapsed_min)
        if v > 0:
            return f" +{v}/m"
        if v < 0:
            return f" {v}/m"
        return ""

    def on_counts_updated(self, counts: ManifestCounts) -> None:
        import time

        resolved = counts.uploaded + counts.available + counts.absent
        t = counts.total or 1

        now = time.monotonic()
        if self._start_time is None:
            self._start_time = now
            self._start_uploaded = counts.uploaded
            self._start_absent = counts.absent
            self._start_unknown = counts.unknown

        elapsed_min = (now - self._start_time) / 60.0

        v_uploaded = self._vel(counts.uploaded - self._start_uploaded, elapsed_min)
        v_absent = self._vel(counts.absent - self._start_absent, elapsed_min)
        v_unknown = self._vel(counts.unknown - self._start_unknown, elapsed_min)

        desc = (
            f"[bold green]On IA: {counts.uploaded} ({counts.uploaded * 100 // t}%){v_uploaded}[/bold green]  "
            f"[yellow]Pending: {counts.available}[/yellow]  "
            f"[dim]Absent: {counts.absent} ({counts.absent * 100 // t}%){v_absent}[/dim]  "
            f"[red]Unknown: {counts.unknown} ({counts.unknown * 100 // t}%){v_unknown}[/red]"
        )
        self.progress.update(
            self.main_task,
            description=desc,
            completed=resolved,
            total=counts.total,
        )

    def on_log(self, message: str) -> None:
        self.progress.console.log(message)

    def on_subtask(self, name: str, total: int) -> None:
        task_id = self.progress.add_task(f"[cyan]{name}", total=total)
        self._subtasks[name] = task_id

    def on_subtask_advance(self, name: str, delta: int = 1) -> None:
        task_id = self._subtasks.get(name)
        if task_id is not None:
            self.progress.advance(task_id, delta)

    def on_subtask_done(self, name: str) -> None:
        task_id = self._subtasks.pop(name, None)
        if task_id is not None:
            self.progress.remove_task(task_id)


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
    exit_code: int,
    *,
    dry_run: bool,
    tribunal: str | None,
    counts: ManifestCounts,
    interrupted: bool = False,
) -> None:
    if interrupted:
        title = "Run Interrupted"
        border = "yellow"
        status = "[yellow]Interrupted[/yellow]"
    elif exit_code == 0:
        title = "Run Complete"
        border = "green"
        status = "[green]OK[/green]"
    else:
        title = "Run Finished With Errors"
        border = "red"
        status = "[red]Error[/red]"
    rows = Table.grid(padding=(0, 2))
    rows.add_column(style="bold cyan")
    rows.add_column()
    rows.add_row("Status:", status)
    rows.add_row("Mode:", "Dry run" if dry_run else "Live upload")
    rows.add_row("Tribunal:", tribunal or "All")
    rows.add_row("Uploaded:", str(counts.uploaded))
    rows.add_row("Available:", str(counts.available))
    rows.add_row("Absent:", str(counts.absent))
    rows.add_row("Unknown:", str(counts.unknown))
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
[bold white]DJEN Backup Engine v3.0 - Manifest-Driven Sync[/bold white]
"""
    console.print(Panel(banner, border_style="green"))


# ── Commands ────────────────────────────────────────────────────────


def _run_pipeline(  # noqa: PLR0913
    *,
    start_date: str | None,
    end_date: str | None,
    tribunal: str | None,
    deadline_minutes: int,
    max_items: int,
    workers: int,
    manifest_file: Path,
    dry_run: bool,
    fail_fast: bool,
    publish_live_status: bool,
    skip_if_mostly_complete: bool,
    use_proxy: bool,
    check_only: bool = False,
    upload_only: bool = False,
    mode_label: str = "Sync",
) -> None:
    """Shared pipeline runner for main/check/upload subcommands."""
    env_result = _load_local_env()
    show_banner()
    _show_env_hint(env_result)

    today = datetime.now(tz=UTC).date()
    resolved_end = _parse_date(end_date) if end_date else today - timedelta(days=1)
    resolved_start = _parse_date(start_date) if start_date else date(2020, 1, 1)
    resolved_use_proxy = use_proxy or _env_truthy("DJEN_USE_PROXY")
    resolved_djen_url = _resolve_djen_url(use_proxy=resolved_use_proxy)

    config_table = Table.grid(padding=(0, 2))
    config_table.add_column(style="bold cyan")
    config_table.add_column()
    config_table.add_row("Mode:", f"[bold magenta]{mode_label}[/bold magenta]")
    config_table.add_row("End Date:", resolved_end.isoformat())
    config_table.add_row("Start Date:", resolved_start.isoformat())
    config_table.add_row("Tribunal:", tribunal or "All")
    config_table.add_row("Deadline:", f"{deadline_minutes} min")
    config_table.add_row("Max Items:", str(max_items) if max_items else "Unlimited")
    config_table.add_row("Workers:", str(workers))
    config_table.add_row("Dry Run:", "[yellow]Yes[/yellow]" if dry_run else "[green]No[/green]")
    config_table.add_row("Fail Fast:", "[red]Yes[/red]" if fail_fast else "[green]No[/green]")
    config_table.add_row("Manifest:", str(manifest_file))
    config_table.add_row("DJEN Mode:", "Proxy" if resolved_use_proxy else "Direct")
    config_table.add_row("DJEN URL:", resolved_djen_url)

    console.print(
        Panel(config_table, title="[bold white]Run Configuration[/bold white]", border_style="blue")
    )

    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        expand=True,
    )

    observer = RichManifestObserver(progress)

    config = SyncConfig(
        start_date=resolved_end,
        lower_bound=resolved_start,
        tribunal=tribunal,
        deadline_minutes=deadline_minutes,
        max_items=max_items,
        workers=workers,
        manifest_file=manifest_file,
        djen_proxy_url=resolved_djen_url,
        ia_auth=_resolve_ia_auth(dry_run=dry_run),
        dry_run=dry_run,
        fail_fast=fail_fast,
        publish_live_status=publish_live_status,
        skip_if_mostly_complete=skip_if_mostly_complete,
        check_only=check_only,
        upload_only=upload_only,
        observer=observer,
    )

    interrupted = False
    try:
        with Live(Group(progress), console=console, refresh_per_second=4):
            exit_code = asyncio.run(run_sync(config))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted — manifest saved to disk.[/yellow]")
        exit_code = 130
        interrupted = True

    final_manifest = SyncManifest()
    final_manifest.load_from_disk(manifest_file)
    final_counts = final_manifest.counts()

    _show_run_summary(
        exit_code,
        dry_run=dry_run,
        tribunal=tribunal,
        counts=final_counts,
        interrupted=interrupted,
    )
    raise typer.Exit(code=exit_code)


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
    max_items: int = typer.Option(0, "--max-items", help="Max downloads per run (0 = unlimited)."),
    workers: int = typer.Option(DEFAULT_WORKERS, "--workers", help="Parallel workers (default: discovered safe limit)."),
    manifest_file: Path = typer.Option(
        Path("data/sync-manifest.csv"), "--manifest-file", help="Path to manifest CSV."
    ),
    *,
    dry_run: bool = typer.Option(False, "--dry-run", help="Log actions without uploading."),
    fail_fast: bool = typer.Option(
        True,
        "--fail-fast/--no-fail-fast",
        help="Stop on first error. Use --no-fail-fast to continue past failures.",
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
    """Main backup and sync command (check + download + upload)."""
    if ctx.invoked_subcommand:
        return
    _run_pipeline(
        start_date=start_date,
        end_date=end_date,
        tribunal=tribunal,
        deadline_minutes=deadline_minutes,
        max_items=max_items,
        workers=workers,
        manifest_file=manifest_file,
        dry_run=dry_run,
        fail_fast=fail_fast,
        publish_live_status=publish_live_status,
        skip_if_mostly_complete=skip_if_mostly_complete,
        use_proxy=use_proxy,
        mode_label="Full Sync",
    )


@app.command()
def check(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
    tribunal: str | None = typer.Option(None, "--tribunal"),
    deadline_minutes: int = typer.Option(45, "--deadline-minutes"),
    workers: int = typer.Option(DEFAULT_WORKERS, "--workers"),
    manifest_file: Path = typer.Option(Path("data/sync-manifest.csv"), "--manifest-file"),
    *,
    fail_fast: bool = typer.Option(True, "--fail-fast/--no-fail-fast"),
    use_proxy: bool = typer.Option(False, "--use-proxy"),
) -> None:
    """Check-only: verify DJEN availability of unknown entries. No downloads."""
    _run_pipeline(
        start_date=start_date,
        end_date=end_date,
        tribunal=tribunal,
        deadline_minutes=deadline_minutes,
        max_items=0,
        workers=workers,
        manifest_file=manifest_file,
        dry_run=False,
        fail_fast=fail_fast,
        publish_live_status=False,
        skip_if_mostly_complete=False,
        use_proxy=use_proxy,
        check_only=True,
        mode_label="Check Only",
    )


@app.command()
def upload(
    tribunal: str | None = typer.Option(None, "--tribunal"),
    deadline_minutes: int = typer.Option(45, "--deadline-minutes"),
    max_items: int = typer.Option(0, "--max-items"),
    workers: int = typer.Option(DEFAULT_WORKERS, "--workers"),
    manifest_file: Path = typer.Option(Path("data/sync-manifest.csv"), "--manifest-file"),
    *,
    fail_fast: bool = typer.Option(True, "--fail-fast/--no-fail-fast"),
    use_proxy: bool = typer.Option(False, "--use-proxy"),
) -> None:
    """Upload-only: download and upload already-available entries. No checks."""
    _run_pipeline(
        start_date=None,
        end_date=None,
        tribunal=tribunal,
        deadline_minutes=deadline_minutes,
        max_items=max_items,
        workers=workers,
        manifest_file=manifest_file,
        dry_run=False,
        fail_fast=fail_fast,
        publish_live_status=False,
        skip_if_mostly_complete=False,
        use_proxy=use_proxy,
        upload_only=True,
        mode_label="Upload Only",
    )


@app.command()
def reset(
    tribunal: str | None = typer.Option(None, "--tribunal", help="Tribunal code to reset."),
    *,
    reset_all: bool = typer.Option(False, "--all", help="Reset all entries for the tribunal."),
    manifest_file: Path = typer.Option(
        Path("data/sync-manifest.csv"), "--manifest-file", help="Path to manifest CSV."
    ),
):
    """Reset manifest entries for a tribunal (clears djen_status and ia_status)."""
    if not tribunal and not reset_all:
        console.print("[bold red]Error:[/bold red] provide --tribunal CODE or --all")
        raise typer.Exit(code=1)

    manifest = SyncManifest()
    manifest.load_from_disk(manifest_file)

    if not manifest:
        console.print("[bold red]Error:[/bold red] manifest file not found or empty.")
        raise typer.Exit(code=1)

    # Reset entries by rebuilding without the targeted entries
    count = 0
    for k, entry in list(manifest._entries.items()):
        if reset_all or (tribunal and entry.tribunal == tribunal.upper()):
            entry.ia_status = ""
            entry.djen_status = ""
            entry.updated_at = ""
            count += 1

    if count > 0:
        manifest.save_to_disk(manifest_file)
        console.print(f"[green]Reset {count} entries.[/green]")
    else:
        console.print("[yellow]Nothing to reset.[/yellow]")


if __name__ == "__main__":
    app()
