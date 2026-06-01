"""CLI entry point for ``djen-backup`` with Typer and Rich."""

from __future__ import annotations

import contextlib

# Safely reconfigure standard output and standard error encoding error handling on Windows
import sys


for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        with contextlib.suppress(AttributeError):
            stream.reconfigure(errors="replace")

import asyncio
import os
from dataclasses import dataclass
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
from djen_backup.drain import PARQUET_URL
from djen_backup.drain import drain as _drain
from djen_backup.engine import SyncConfig, SyncSummary, load_djen_safe_concurrency, run_sync
from djen_backup.manifest import ManifestCounts, SyncManifest
from djen_backup.probe import PARQUET_URL as _PROBE_PARQUET_URL
from djen_backup.probe import probe as _probe


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
            f"[bold green]On IA: {counts.uploaded} "
            f"({counts.uploaded * 100 // t}%){v_uploaded}[/bold green]  "
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
    summary: SyncSummary,
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

    counts = summary.final_counts or ManifestCounts(0, 0, 0, 0, 0)

    # Session Gains
    real_uploads = summary.uploads
    discovered = (counts.uploaded - summary.initial_uploaded) - real_uploads
    backfill_advance = counts.uploaded - summary.initial_uploaded

    total = counts.total or 1
    coverage = counts.uploaded * 100 // total

    rows = Table.grid(padding=(0, 2))
    rows.add_column(style="bold cyan")
    rows.add_column()
    rows.add_row("Status:", status)
    rows.add_row("Mode:", "Dry run" if dry_run else "Live upload")
    rows.add_row("Tribunal:", tribunal or "All")

    rows.add_row("", "")
    rows.add_row("[bold white]Session Progress:[/bold white]", "")
    rows.add_row("  Real Uploads:", f"[green]{real_uploads}[/green]")
    rows.add_row("  IA Discoveries:", f"[blue]{max(0, discovered)}[/blue]")
    rows.add_row("  Net Advance:", f"[bold green]+{backfill_advance}[/bold green] entries")

    rows.add_row("", "")
    rows.add_row("[bold white]Global State:[/bold white]", "")
    rows.add_row("  Total IA:", f"{counts.uploaded} ({coverage}%)")
    rows.add_row("  Pending:", str(counts.available))
    rows.add_row("  Absent:", str(counts.absent))
    rows.add_row("  Unknown:", str(counts.unknown))

    console.print(
        Panel(rows, title=f"[bold white]{title}[/bold white]", border_style=border, expand=False)
    )


@dataclass
class PipelineRunConfig:
    start_date: date
    end_date: date
    lower_bound: date | None
    tribunal: str | None
    deadline_minutes: int
    max_items: int
    workers: int
    fail_fast: bool
    publish_live_status: bool
    skip_if_mostly_complete: bool
    use_proxy: bool
    upload_only: bool = False
    check_only: bool = False
    mode_label: str = "Full Sync"


def _run_pipeline(c: PipelineRunConfig) -> int:
    env_result = _load_local_env()
    show_banner()
    _show_env_hint(env_result)

    djen_url = _resolve_djen_url(use_proxy=c.use_proxy)
    auth = _resolve_ia_auth(dry_run=False)

    config_table = Table.grid(padding=(0, 2))
    config_table.add_column(style="bold cyan")
    config_table.add_column()
    config_table.add_row("Mode:", c.mode_label)
    config_table.add_row("End Date:", c.end_date.isoformat())
    config_table.add_row("Start Date:", (c.lower_bound or date(2020, 1, 1)).isoformat())
    config_table.add_row("Tribunal:", c.tribunal or "All")
    config_table.add_row("Deadline:", f"{c.deadline_minutes} min")
    config_table.add_row("Max Items:", str(c.max_items) if c.max_items else "Unlimited")
    config_table.add_row("Workers:", str(c.workers))
    config_table.add_row("Dry Run:", "Yes" if False else "No")
    config_table.add_row("Fail Fast:", "Yes" if c.fail_fast else "No")
    config_table.add_row("Manifest:", "data/sync-manifest.csv")
    config_table.add_row("DJEN Mode:", "Proxy" if c.use_proxy else "Direct")
    config_table.add_row("DJEN URL:", djen_url)
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
    )
    observer = RichManifestObserver(progress)

    sync_config = SyncConfig(
        start_date=c.end_date,
        lower_bound=c.lower_bound,
        tribunal=c.tribunal,
        deadline_minutes=c.deadline_minutes,
        max_items=c.max_items,
        workers=c.workers,
        manifest_file=Path("data/sync-manifest.csv"),
        djen_proxy_url=djen_url,
        ia_auth=auth,
        dry_run=False,
        fail_fast=c.fail_fast,
        publish_live_status=c.publish_live_status,
        skip_if_mostly_complete=c.skip_if_mostly_complete,
        check_only=c.check_only,
        upload_only=c.upload_only,
        observer=observer,
    )

    exit_code = 0
    interrupted = False
    try:
        with Live(Group(progress), console=console, refresh_per_second=4):
            exit_code, summary = asyncio.run(run_sync(sync_config))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted — manifest saved to disk.[/yellow]")
        return 130

    _show_run_summary(
        exit_code,
        dry_run=False,
        tribunal=c.tribunal,
        summary=summary,
        interrupted=interrupted,
    )
    return exit_code


# ── Commands ────────────────────────────────────────────────────────


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    start_date: str = typer.Option("2020-01-01", help="Lower bound for history."),
    end_date: str = typer.Option(
        (date.today() - timedelta(days=1)).isoformat(), help="Upper bound for history."
    ),
    tribunal: str | None = typer.Option(None, help="Specific tribunal code."),
    deadline_minutes: int = typer.Option(17, help="Stop processing after N minutes."),
    max_items: int = typer.Option(0, help="Stop after N successful uploads."),
    workers: int = typer.Option(DEFAULT_WORKERS, help="Number of concurrent workers."),
    fail_fast: bool = typer.Option(True, help="Stop on first error."),
    use_proxy: bool = typer.Option(False, help="Use DJEN proxy."),
) -> None:
    """Main backup and sync command (check + download + upload)."""
    if ctx.invoked_subcommand:
        return
    _run_pipeline(
        PipelineRunConfig(
            start_date=date(2020, 1, 1),
            end_date=_parse_date(end_date),
            lower_bound=_parse_date(start_date),
            tribunal=tribunal,
            deadline_minutes=deadline_minutes,
            max_items=max_items,
            workers=workers,
            fail_fast=fail_fast,
            publish_live_status=False,
            skip_if_mostly_complete=False,
            use_proxy=use_proxy,
        )
    )


@app.command()
def check(
    start_date: str = typer.Option("2020-01-01", help="Lower bound for history."),
    end_date: str = typer.Option(
        (date.today() - timedelta(days=1)).isoformat(), help="Upper bound for history."
    ),
    tribunal: str | None = typer.Option(None, help="Specific tribunal code."),
    deadline_minutes: int = typer.Option(17, help="Stop processing after N minutes."),
    workers: int = typer.Option(DEFAULT_WORKERS, help="Number of concurrent workers."),
    fail_fast: bool = typer.Option(True, help="Stop on first error."),
    use_proxy: bool = typer.Option(False, help="Use DJEN proxy."),
) -> None:
    """Check DJEN availability without downloading/uploading."""
    _run_pipeline(
        PipelineRunConfig(
            start_date=date(2020, 1, 1),
            end_date=_parse_date(end_date),
            lower_bound=_parse_date(start_date),
            tribunal=tribunal,
            deadline_minutes=deadline_minutes,
            max_items=0,
            workers=workers,
            fail_fast=fail_fast,
            publish_live_status=False,
            skip_if_mostly_complete=False,
            use_proxy=use_proxy,
            check_only=True,
            mode_label="Check Only",
        )
    )


@app.command()
def upload(
    tribunal: str | None = typer.Option(None, help="Specific tribunal code."),
    deadline_minutes: int = typer.Option(17, help="Stop processing after N minutes."),
    max_items: int = typer.Option(0, help="Stop after N successful uploads."),
    workers: int = typer.Option(DEFAULT_WORKERS, help="Number of concurrent workers."),
    fail_fast: bool = typer.Option(True, help="Stop on first error."),  # noqa: FBT001, FBT003
    use_proxy: bool = typer.Option(False, help="Use DJEN proxy."),  # noqa: FBT001, FBT003
) -> None:
    """Upload already-discovered available entries (backlog drain)."""
    _run_pipeline(
        PipelineRunConfig(
            start_date=date(2020, 1, 1),
            end_date=datetime.now(UTC).date(),
            lower_bound=None,
            tribunal=tribunal,
            deadline_minutes=deadline_minutes,
            max_items=max_items,
            workers=workers,
            fail_fast=fail_fast,
            publish_live_status=False,
            skip_if_mostly_complete=False,
            use_proxy=use_proxy,
            upload_only=True,
            mode_label="Upload Only",
        )
    )


@app.command()
def drain(
    workers: int = typer.Option(6, "--workers", help="Concurrent download+upload workers."),
    batch_size: int = typer.Option(100, "--batch-size", help="Pending entries fetched per batch."),
    deadline_minutes: int = typer.Option(
        14, "--deadline-minutes", help="Stop fetching new batches after this many minutes."
    ),
    *,
    use_proxy: bool = typer.Option(False, "--use-proxy", help="Use the Cloud Run DJEN proxy."),  # noqa: FBT003
) -> None:
    """Batched upload-only drain via remote sync-manifest.parquet (no full manifest load)."""
    env_result = _load_local_env()
    show_banner()
    _show_env_hint(env_result)

    resolved_use_proxy = use_proxy or _env_truthy("DJEN_USE_PROXY")
    djen_url = _resolve_djen_url(use_proxy=resolved_use_proxy)
    auth = _resolve_ia_auth(dry_run=False)

    config_table = Table.grid(padding=(0, 2))
    config_table.add_column(style="bold cyan")
    config_table.add_column()
    config_table.add_row("Mode:", "[bold magenta]Drain (remote parquet)[/bold magenta]")
    config_table.add_row("Workers:", str(workers))
    config_table.add_row("Batch size:", str(batch_size))
    config_table.add_row("Deadline:", f"{deadline_minutes} min")
    config_table.add_row("Parquet:", PARQUET_URL)
    config_table.add_row("DJEN URL:", djen_url)
    console.print(
        Panel(
            config_table, title="[bold white]Drain Configuration[/bold white]", border_style="blue"
        )
    )

    uploads = asyncio.run(
        _drain(
            workers=workers,
            batch_size=batch_size,
            deadline_seconds=deadline_minutes * 60,
            djen_proxy_url=djen_url,
            ia_auth=auth,
        )
    )
    console.print(
        Panel(f"[bold green]Uploads completed:[/bold green] {uploads}", border_style="green")
    )


@app.command()
def probe(
    workers: int = typer.Option(20, "--workers", help="Concurrent probe workers (URL check only)."),
    batch_size: int = typer.Option(500, "--batch-size", help="Pending entries fetched per batch."),
    deadline_minutes: int = typer.Option(
        13, "--deadline-minutes", help="Stop fetching new batches after this many minutes."
    ),
    *,
    use_proxy: bool = typer.Option(False, "--use-proxy", help="Use the Cloud Run DJEN proxy."),  # noqa: FBT003
) -> None:
    """Probe DJEN availability for pending entries — no download, no IA upload.

    Marks 404s as absent and found URLs as confirmed in a delta CSV uploaded
    to IA. Run in parallel with ``drain`` for maximum throughput.
    """
    env_result = _load_local_env()
    show_banner()
    _show_env_hint(env_result)

    resolved_use_proxy = use_proxy or _env_truthy("DJEN_USE_PROXY")
    djen_url = _resolve_djen_url(use_proxy=resolved_use_proxy)
    auth = _resolve_ia_auth(dry_run=False)

    config_table = Table.grid(padding=(0, 2))
    config_table.add_column(style="bold cyan")
    config_table.add_column()
    config_table.add_row("Mode:", "[bold yellow]Probe (URL check only)[/bold yellow]")
    config_table.add_row("Workers:", str(workers))
    config_table.add_row("Batch size:", str(batch_size))
    config_table.add_row("Deadline:", f"{deadline_minutes} min")
    config_table.add_row("Parquet:", _PROBE_PARQUET_URL)
    config_table.add_row("DJEN URL:", djen_url)
    console.print(
        Panel(
            config_table,
            title="[bold white]Probe Configuration[/bold white]",
            border_style="yellow",
        )
    )

    confirmed, absent = asyncio.run(
        _probe(
            workers=workers,
            batch_size=batch_size,
            deadline_seconds=deadline_minutes * 60,
            djen_proxy_url=djen_url,
            ia_auth=auth,
        )
    )
    console.print(
        Panel(
            f"[bold green]Confirmed:[/bold green] {confirmed}  "
            f"[bold red]Absent (404):[/bold red] {absent}",
            border_style="yellow",
        )
    )


@app.command()
def reset(
    tribunal: str | None = typer.Option(None, "--tribunal", help="Tribunal code to reset."),
    *,
    reset_all: bool = typer.Option(False, "--all", help="Reset all entries for the tribunal."),  # noqa: FBT003
    manifest_file: Path = typer.Option(
        Path("data/sync-manifest.csv"), "--manifest-file", help="Path to manifest CSV."
    ),
) -> None:
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
    for _k, entry in list(manifest._entries.items()):  # noqa: SLF001
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


def show_banner() -> None:
    """Print the ASCII art banner."""
    banner = r"""
    ______                               ______            __
   / ____/___ ___  __________ __________ _/ ____/___ _____  / /_  ____ _
  / /   / __ `/ / / / ___/ __ `/ ___/ __ `/ / __/ __ `/ __ \/ __ \/ __ `/
 / /___/ /_/ / /_/ (__  ) /_/ / /  / /_/ / /_/ / /_/ / / / / / / / /_/ /
 \____/\__,_/\__,_/____/\__,_/_/   \__,_/\____/\__,_/ / /_/_/ /_/\__,_/

 DJEN Backup Engine v3.0 - Manifest-Driven Sync
                                                                              """
    console.print(Panel(banner, border_style="cyan"))


if __name__ == "__main__":
    app()
