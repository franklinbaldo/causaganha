"""CLI entry point for ``djen-backup`` with Cyclopts and Rich."""

from __future__ import annotations

import asyncio
import contextlib
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated, NamedTuple

import structlog
from cyclopts import App, Parameter
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

from djen_backup import service
from djen_backup.drain import PARQUET_URL
from djen_backup.engine import SyncSummary, load_djen_safe_concurrency
from djen_backup.manifest import ManifestCounts
from djen_backup.probe import PARQUET_URL as _PROBE_PARQUET_URL
from djen_backup.service import MissingCredentialsError, PipelineRunConfig


# Default worker count — discovered via scripts/stress_test_djen.py
DEFAULT_WORKERS = load_djen_safe_concurrency()


def configure_runtime() -> None:
    """Reconfigure stdio encoding and structlog for CLI use.

    Called once, from the meta-app launcher below (``_launch``, registered
    via ``_commands_app.meta.default``), before any command body runs —
    Cyclopts always calls the meta app's default first and only then
    dispatches to the real command, so this covers every subcommand too
    (RFC 0013 Fase 4; matches the guarantee Click's group callback used to
    give under Typer). Previously ran at
    import time, which meant anything importing this module (a test, a
    future MCP server process) silently reconfigured the whole process's
    stdout/stderr and global structlog state.
    """
    for stream in (sys.stdout, sys.stderr):
        if stream and stream.encoding and stream.encoding.lower() != "utf-8":
            with contextlib.suppress(AttributeError):
                stream.reconfigure(errors="replace")

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


class EnvLoadResult(NamedTuple):
    path: Path
    loaded_keys: list[str]


# ── Setup ───────────────────────────────────────────────────────────

_commands_app = App(
    name="djen-backup",
    help="Back up DJEN judicial communications to the Internet Archive.",
    # Cyclopts registers --version by default; the original Typer app never
    # declared it, so leaving it on would silently accept a form that used
    # to be a usage error (RFC 0013 Fase 4 review, #855 round 3). The meta
    # app (`app = _commands_app.meta`, below) is checked separately — see
    # its own comment.
    version_flags=[],
)
console = Console()

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


def _resolve_ia_auth() -> str:
    try:
        return service.resolve_ia_auth()
    except MissingCredentialsError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise SystemExit(1) from exc


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


def _run_pipeline(c: PipelineRunConfig) -> int:
    env_result = _load_local_env()
    show_banner()
    _show_env_hint(env_result)

    djen_url = service.resolve_djen_url(use_proxy=c.use_proxy)
    auth = _resolve_ia_auth()

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
    config_table.add_row("Dry Run:", "No")
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

    exit_code = 0
    interrupted = False
    try:
        with Live(Group(progress), console=console, refresh_per_second=4):
            exit_code, summary = asyncio.run(
                service.run_pipeline(c, djen_url=djen_url, ia_auth=auth, observer=observer)
            )
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


@_commands_app.default
def main(
    *,
    start_date: Annotated[str, Parameter(help="Lower bound for history.")] = "2020-01-01",
    end_date: Annotated[str, Parameter(help="Upper bound for history.")] = (
        date.today() - timedelta(days=1)
    ).isoformat(),
    tribunal: Annotated[str | None, Parameter(help="Specific tribunal code.")] = None,
    deadline_minutes: Annotated[int, Parameter(help="Stop processing after N minutes.")] = 17,
    max_items: Annotated[int, Parameter(help="Stop after N successful uploads.")] = 0,
    workers: Annotated[int, Parameter(help="Number of concurrent workers.")] = DEFAULT_WORKERS,
    fail_fast: Annotated[bool, Parameter(help="Stop on first error.")] = True,
    use_proxy: Annotated[bool, Parameter(help="Use DJEN proxy.")] = False,
) -> int:
    """Main backup and sync command (check + download + upload).

    Only fires when no subcommand token matches (Cyclopts' `@_commands_app.default` —
    the equivalent of Typer's `invoke_without_command=True`); `configure_runtime()`
    itself runs unconditionally for every invocation via the meta-app
    launcher below, not here.
    """
    return _run_pipeline(
        PipelineRunConfig(
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


@_commands_app.command
def check(
    *,
    start_date: Annotated[str, Parameter(help="Lower bound for history.")] = "2020-01-01",
    end_date: Annotated[str, Parameter(help="Upper bound for history.")] = (
        date.today() - timedelta(days=1)
    ).isoformat(),
    tribunal: Annotated[str | None, Parameter(help="Specific tribunal code.")] = None,
    deadline_minutes: Annotated[int, Parameter(help="Stop processing after N minutes.")] = 17,
    workers: Annotated[int, Parameter(help="Number of concurrent workers.")] = DEFAULT_WORKERS,
    fail_fast: Annotated[bool, Parameter(help="Stop on first error.")] = True,
    use_proxy: Annotated[bool, Parameter(help="Use DJEN proxy.")] = False,
) -> int:
    """Check DJEN availability without downloading/uploading."""
    return _run_pipeline(
        PipelineRunConfig(
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


@_commands_app.command
def upload(
    *,
    tribunal: Annotated[str | None, Parameter(help="Specific tribunal code.")] = None,
    deadline_minutes: Annotated[int, Parameter(help="Stop processing after N minutes.")] = 17,
    max_items: Annotated[int, Parameter(help="Stop after N successful uploads.")] = 0,
    workers: Annotated[int, Parameter(help="Number of concurrent workers.")] = DEFAULT_WORKERS,
    fail_fast: Annotated[bool, Parameter(help="Stop on first error.")] = True,
    use_proxy: Annotated[bool, Parameter(help="Use DJEN proxy.")] = False,
) -> int:
    """Upload already-discovered available entries (backlog drain)."""
    return _run_pipeline(
        PipelineRunConfig(
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


@_commands_app.command
def drain(
    *,
    workers: Annotated[
        int, Parameter(name="--workers", help="Concurrent download+upload workers.")
    ] = 6,
    batch_size: Annotated[
        int, Parameter(name="--batch-size", help="Pending entries fetched per batch.")
    ] = 100,
    deadline_minutes: Annotated[
        int,
        Parameter(
            name="--deadline-minutes",
            help="Stop fetching new batches after this many minutes.",
        ),
    ] = 14,
    # negative=[]: no --no-use-proxy pair here, unlike the bare callback's
    # use_proxy — matches the original Typer behavior, where passing an
    # explicit option string ("--use-proxy") suppressed the auto-negation
    # Typer otherwise infers. Cyclopts doesn't suppress it just from an
    # explicit `name=`, so this has to be spelled out (RFC 0013 Fase 4's
    # most fragile case — verified by direct experiment before writing this).
    use_proxy: Annotated[
        bool,
        Parameter(name="--use-proxy", negative=[], help="Use the Cloud Run DJEN proxy."),
    ] = False,
) -> None:
    """Batched upload-only drain via remote sync-manifest.parquet (no full manifest load)."""
    env_result = _load_local_env()
    show_banner()
    _show_env_hint(env_result)

    resolved_use_proxy = use_proxy or _env_truthy("DJEN_USE_PROXY")
    djen_url = service.resolve_djen_url(use_proxy=resolved_use_proxy)
    auth = _resolve_ia_auth()

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
        service.run_drain(
            workers=workers,
            batch_size=batch_size,
            deadline_minutes=deadline_minutes,
            djen_url=djen_url,
            ia_auth=auth,
        )
    )
    console.print(
        Panel(f"[bold green]Uploads completed:[/bold green] {uploads}", border_style="green")
    )


@_commands_app.command
def probe(
    *,
    workers: Annotated[
        int, Parameter(name="--workers", help="Concurrent probe workers (URL check only).")
    ] = 20,
    batch_size: Annotated[
        int, Parameter(name="--batch-size", help="Pending entries fetched per batch.")
    ] = 500,
    deadline_minutes: Annotated[
        int,
        Parameter(
            name="--deadline-minutes",
            help="Stop fetching new batches after this many minutes.",
        ),
    ] = 13,
    # negative=[]: same rationale as drain's use_proxy above.
    use_proxy: Annotated[
        bool,
        Parameter(name="--use-proxy", negative=[], help="Use the Cloud Run DJEN proxy."),
    ] = False,
) -> None:
    """Probe DJEN availability for pending entries — no download, no IA upload.

    Marks 404s as absent and found URLs as confirmed in a delta CSV uploaded
    to IA. Run in parallel with ``drain`` for maximum throughput.
    """
    env_result = _load_local_env()
    show_banner()
    _show_env_hint(env_result)

    resolved_use_proxy = use_proxy or _env_truthy("DJEN_USE_PROXY")
    djen_url = service.resolve_djen_url(use_proxy=resolved_use_proxy)
    auth = _resolve_ia_auth()

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
        service.run_probe(
            workers=workers,
            batch_size=batch_size,
            deadline_minutes=deadline_minutes,
            djen_url=djen_url,
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


@_commands_app.command
def reset(
    *,
    tribunal: Annotated[
        str | None, Parameter(name="--tribunal", help="Tribunal code to reset.")
    ] = None,
    # negative=[]: the original Typer option ("--all", explicit string) had
    # no --no-all pair; same rationale as drain/probe's use_proxy above.
    reset_all: Annotated[
        bool,
        Parameter(name="--all", negative=[], help="Reset all entries for the tribunal."),
    ] = False,
    manifest_file: Annotated[
        Path, Parameter(name="--manifest-file", help="Path to manifest CSV.")
    ] = Path("data/sync-manifest.csv"),
) -> int:
    """Reset manifest entries for a tribunal (clears djen_status and ia_status)."""
    if not tribunal and not reset_all:
        console.print("[bold red]Error:[/bold red] provide --tribunal CODE or --all")
        return 1

    try:
        result = service.reset_manifest(manifest_file, tribunal=tribunal, reset_all=reset_all)
    except service.ManifestNotFoundError:
        console.print("[bold red]Error:[/bold red] manifest file not found or empty.")
        return 1

    if result.count > 0:
        console.print(f"[green]Reset {result.count} entries.[/green]")
    else:
        console.print("[yellow]Nothing to reset.[/yellow]")
    return 0


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


@_commands_app.meta.default
def _launch(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
) -> int:
    """Meta-app launcher — runs ``configure_runtime()`` before every dispatch.

    Cyclopts' meta-app pattern (``App.meta``) is the equivalent of what
    Click's group callback used to guarantee under Typer: this runs first
    for both the bare invocation and every subcommand, unconditionally,
    before delegating to ``_commands_app`` for real argv parsing/dispatch.
    The public ``app`` name below is bound to this meta app specifically —
    not to ``_commands_app`` — so that both the ``causaganha-mcp``-style
    console-script entry point and `tests/cli_contract`'s `module.app`
    convention go through this launcher, matching production.
    """
    configure_runtime()
    return _commands_app(tokens)


app = _commands_app.meta


if __name__ == "__main__":
    app()
