"""CLI command module for CausaGanha backfill pipeline."""

import asyncio
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import structlog
import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from djen_backup.backfill import (
    BackfillConfig,
    load_backfill_state,
    run_backfill,
    save_backfill_state,
)


app = typer.Typer(
    help="Manage the DJEN backfill pipeline and Internet Archive uploads.",
    no_args_is_help=True,
)

console = Console()


def _setup_backfill_logging(log_file: Path, verbose: bool = False) -> None:
    """Configure logging for the backfill run: file (DEBUG) + console (Rich)."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    # File handler: everything in detail
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s  %(message)s"))
    root.addHandler(fh)

    # Console handler: Rich, WARNING+ (or DEBUG if verbose)
    rh = RichHandler(
        console=Console(stderr=True),
        show_time=True,
        show_path=False,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
        level=logging.DEBUG if verbose else logging.WARNING,
    )
    root.addHandler(rh)

    # Silence noisy HTTP debug logs
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("hpack").setLevel(logging.WARNING)

    # Bridge structlog → stdlib logging
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )


def _resolve_ia_auth() -> str:
    """Build the IA S3 auth header from environment."""
    access = os.environ.get("IAS3_ACCESS_KEY") or os.environ.get("IA_ACCESS_KEY", "")
    secret = os.environ.get("IAS3_SECRET_KEY") or os.environ.get("IA_SECRET_KEY", "")
    return f"LOW {access}:{secret}"


DJEN_DIRECT_URL = "https://comunicaapi.pje.jus.br"


def _resolve_djen_url(*, use_proxy: bool = False) -> str:
    """Get the DJEN URL. Direct by default, proxy when outside Brazil."""
    if use_proxy:
        from causaganha.config import DJEN_PROXY_URL
        return os.environ.get("DJEN_PROXY_URL", DJEN_PROXY_URL)
    return os.environ.get("DJEN_PROXY_URL", DJEN_DIRECT_URL)


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m{secs:.0f}s"


def _preflight_checks() -> None:
    """Check prerequisites before running. Exits on failure."""
    errors: list[str] = []
    if not os.environ.get("IAS3_ACCESS_KEY") and not os.environ.get("IA_ACCESS_KEY"):
        errors.append("IAS3_ACCESS_KEY (ou IA_ACCESS_KEY) não definido no ambiente")
    if not os.environ.get("IAS3_SECRET_KEY") and not os.environ.get("IA_SECRET_KEY"):
        errors.append("IAS3_SECRET_KEY (ou IA_SECRET_KEY) não definido no ambiente")
    if errors:
        console.print()
        console.print(Panel(
            "\n".join(f"• {e}" for e in errors),
            title="[red bold]Pre-flight check failed[/red bold]",
            border_style="red",
            padding=(1, 2),
        ))
        console.print("  [dim]Configure as variáveis em .env ou exporte no shell.[/dim]\n")
        raise typer.Exit(code=1)


# ── Commands ────────────────────────────────────────────────


@app.command()
def run(
    target_date: str = typer.Option(
        "",
        "--date",
        help="Data específica (YYYY-MM-DD). Default: ontem.",
    ),
    job: str = typer.Option(
        "all",
        help="Step a executar: all, collect, consolidate, embed.",
    ),
    tribunal: str = typer.Option(
        "",
        help="Tribunal específico (ex: TJSP). Default: todos.",
    ),
    max_items: int = typer.Option(
        0,
        help="Máximo de uploads por run (0 = sem limite).",
    ),
    deadline_minutes: int = typer.Option(
        45,
        help="Tempo máximo em minutos.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Mostrar logs detalhados no console.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Simular sem executar.",
    ),
    continue_on_error: bool = typer.Option(
        False,
        "--continue-on-error",
        help="Continuar pipeline mesmo quando um step falha.",
    ),
    use_proxy: bool = typer.Option(
        False,
        "--use-proxy",
        help="Usar proxy Cloud Run para DJEN (necessário fora do Brasil).",
    ),
) -> None:
    """Run the backfill pipeline locally."""
    # Load .env if present
    env_file = Path(__file__).parent.parent.parent.parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

    if not dry_run:
        _preflight_checks()

    # Setup logging
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"pipeline-{date.today().isoformat()}.log"
    _setup_backfill_logging(log_file, verbose=verbose)

    # Resolve config
    today = datetime.now(UTC).date()
    end_date = date.fromisoformat(target_date) if target_date else today - timedelta(days=1)

    config_lines = [
        f"[bold]Data:[/bold]     {end_date.isoformat()}",
        f"[bold]Job:[/bold]      {job}",
        f"[bold]Tribunal:[/bold] {tribunal or 'todos'}",
        f"[bold]Limite:[/bold]   {max_items or 'sem limite'} uploads, {deadline_minutes}min",
        f"[bold]Log:[/bold]      {log_file}",
    ]
    if dry_run:
        config_lines.append("[yellow bold]Modo:[/yellow bold]     dry-run")

    console.print()
    console.print(Panel(
        "\n".join(config_lines),
        title="[bold]Pipeline Run[/bold]",
        border_style="blue",
        padding=(1, 2),
    ))
    console.print()

    if job in ("all", "collect"):
        backfill_config = BackfillConfig(
            start_date=end_date,
            lower_bound=None,
            tribunal=tribunal or None,
            deadline_minutes=deadline_minutes,
            max_items=max_items,
            workers=1,
            backfill_state_file=Path("data/backfill-state.json"),
            state_file=Path("data/ia-state.json"),
            djen_proxy_url=_resolve_djen_url(use_proxy=use_proxy),
            ia_auth=_resolve_ia_auth(),
            dry_run=dry_run,
        )

        console.print("  ⏳ Collect...")
        start = time.time()
        try:
            exit_code = asyncio.run(run_backfill(backfill_config))
            duration = time.time() - start
            if exit_code == 0:
                console.print(
                    f"  [green]✓[/green] Collect         "
                    f"[dim]{_format_duration(duration)}[/dim]"
                )
            else:
                console.print(
                    f"  [red]✗[/red] Collect         "
                    f"[dim]{_format_duration(duration)}[/dim]  exit={exit_code}"
                )
                if not continue_on_error:
                    raise typer.Exit(code=exit_code)
        except Exception as e:
            duration = time.time() - start
            console.print(
                f"  [red]✗[/red] Collect         "
                f"[dim]{_format_duration(duration)}[/dim]"
            )
            console.print(Panel(
                f"[bold]{type(e).__name__}[/bold]: {e}",
                title="[red]Error in Collect[/red]",
                border_style="red",
                padding=(0, 1),
            ))
            if not continue_on_error:
                raise typer.Exit(code=1) from e

    console.print(f"\n  [dim]Log: {log_file}[/dim]\n")


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
        console.print("[dim]No backfill state found.[/dim]")
        return

    running = sum(1 for p in progress.values() if not p.stopped)
    stopped = sum(1 for p in progress.values() if p.stopped)

    table = Table(
        title=f"Backfill Progress — {len(progress)} tribunais ({running} running, {stopped} stopped)",
        border_style="dim",
    )
    table.add_column("Tribunal", style="bold")
    table.add_column("Status")
    table.add_column("Cursor")
    table.add_column("Streak", justify="right")
    table.add_column("Last Hit")

    for code in sorted(progress):
        prog = progress[code]
        status_str = "[red]STOPPED[/red]" if prog.stopped else "[green]running[/green]"
        hit_str = prog.last_hit_date.isoformat() if prog.last_hit_date else "[dim]never[/dim]"
        streak_style = "red" if prog.empty_streak > 30 else "yellow" if prog.empty_streak > 10 else ""
        streak_text = f"[{streak_style}]{prog.empty_streak}[/{streak_style}]" if streak_style else str(prog.empty_streak)

        table.add_row(
            code,
            status_str,
            prog.cursor_date.isoformat(),
            streak_text,
            hit_str,
        )

    console.print()
    console.print(table)
    console.print()


@app.command()
def reset(
    tribunal: str | None = typer.Option(
        None,
        help="Reset a specific tribunal. Omit for --all.",
    ),
    *,
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
    if not tribunal and not all:
        console.print("[red]Error: provide --tribunal CODE or --all[/red]")
        raise typer.Exit(code=1)

    bstate = load_backfill_state(backfill_state_file)
    progress = bstate.get_all_progress()

    async def _reset() -> int:
        count = 0
        if tribunal:
            if await bstate.reset_tribunal(tribunal):
                console.print(f"  [green]✓[/green] Reset {tribunal}")
                count = 1
            else:
                console.print(f"  [red]✗[/red] Tribunal {tribunal} not found in state.")
        else:
            for code, prog in progress.items():
                if prog.stopped:
                    await bstate.reset_tribunal(code)
                    console.print(f"  [green]✓[/green] Reset {code}")
                    count += 1
        return count

    count = asyncio.run(_reset())
    if count > 0:
        save_backfill_state(bstate, backfill_state_file)
        console.print(f"\n  {count} tribunal(s) reset.")
    else:
        console.print("  [dim]Nothing to reset.[/dim]")
