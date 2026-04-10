"""CLI command module for the DJEN backfill pipeline."""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from causaganha.config import DJEN_DIRECT_URL, DJEN_PROXY_URL
from djen_backup.credentials import get_ia_s3_auth
from djen_backup.engine import SyncConfig, SyncState, run_sync


app = typer.Typer(
    help="Manage the DJEN backfill pipeline and Internet Archive uploads.",
    no_args_is_help=True,
)

console = Console()

_DEFAULT_STATE_FILE = Path("data/backfill-state.json")
def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m{secs:.0f}s"


def _resolve_ia_auth(*, dry_run: bool = False) -> str:
    """Get IA S3 auth header; returns a dummy value in dry-run mode."""
    try:
        return get_ia_s3_auth()
    except RuntimeError:
        if dry_run:
            return "LOW dry-run:dry-run"
        raise


def _resolve_djen_url(*, use_proxy: bool) -> str:
    """Get the DJEN URL. Direct by default, proxy when outside Brazil."""
    if use_proxy:
        return os.environ.get("DJEN_PROXY_URL", DJEN_PROXY_URL)
    return os.environ.get("DJEN_DIRECT_URL", DJEN_DIRECT_URL)


def _preflight_checks() -> None:
    """Verify IA credentials are present; exit with a clear message if not."""
    errors: list[str] = []
    if not os.environ.get("IAS3_ACCESS_KEY") and not os.environ.get("IA_ACCESS_KEY"):
        errors.append("IAS3_ACCESS_KEY (ou IA_ACCESS_KEY) não definido no ambiente")
    if not os.environ.get("IAS3_SECRET_KEY") and not os.environ.get("IA_SECRET_KEY"):
        errors.append("IAS3_SECRET_KEY (ou IA_SECRET_KEY) não definido no ambiente")
    if errors:
        console.print()
        console.print(
            Panel(
                "\n".join(f"• {e}" for e in errors),
                title="[red bold]Pre-flight check failed[/red bold]",
                border_style="red",
                padding=(1, 2),
            )
        )
        console.print("  [dim]Configure as variáveis em .env ou exporte no shell.[/dim]\n")
        raise typer.Exit(code=1)


# ── Commands ────────────────────────────────────────────────────────────────


@app.command()
def run(
    target_date: str = typer.Option(
        "",
        "--date",
        help="Data mais recente a sincronizar (YYYY-MM-DD). Default: ontem.",
    ),
    tribunal: str = typer.Option(
        "",
        help="Tribunal específico (ex: TJSP). Default: todos.",
    ),
    max_items: int = typer.Option(
        0,
        help="Máximo de itens por run (0 = sem limite).",
    ),
    deadline_minutes: int = typer.Option(
        45,
        help="Tempo máximo em minutos.",
    ),
    workers: int = typer.Option(
        4,
        help="Workers paralelos.",
    ),
    state_file: Path = typer.Option(
        _DEFAULT_STATE_FILE,
        "--backfill-state-file",
        help="Path ao arquivo JSON de progresso.",
    ),
    *,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Logs detalhados."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simular sem executar uploads."),
    use_proxy: bool = typer.Option(
        False,
        "--use-proxy",
        help="Usar proxy Cloud Run para DJEN (necessário fora do Brasil).",
    ),
) -> None:
    """Run the DJEN ZIP backup sync against the Internet Archive."""
    # Load .env if present
    env_file = Path(__file__).parents[4] / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

    if not dry_run:
        _preflight_checks()

    today = datetime.now(UTC).date()
    end_date = date.fromisoformat(target_date) if target_date else today - timedelta(days=1)

    config_lines = [
        f"[bold]Data:[/bold]     {end_date.isoformat()}",
        f"[bold]Tribunal:[/bold] {tribunal or 'todos'}",
        f"[bold]Limite:[/bold]   {max_items or 'sem limite'} itens, {deadline_minutes}min",
        f"[bold]Workers:[/bold]  {workers}",
        f"[bold]State:[/bold]    {state_file}",
    ]
    if dry_run:
        config_lines.append("[yellow bold]Modo:[/yellow bold]     dry-run")
    if verbose:
        config_lines.append("[dim]Verbose: on[/dim]")

    console.print()
    console.print(
        Panel(
            "\n".join(config_lines),
            title="[bold]DJEN Backup Run[/bold]",
            border_style="blue",
            padding=(1, 2),
        )
    )
    console.print()

    config = SyncConfig(
        start_date=end_date,
        lower_bound=None,
        tribunal=tribunal or None,
        deadline_minutes=deadline_minutes,
        max_items=max_items,
        workers=workers,
        state_file=state_file,
        djen_proxy_url=_resolve_djen_url(
            use_proxy=use_proxy or os.environ.get("DJEN_USE_PROXY", "").lower() in ("1", "true", "yes", "on")
        ),
        ia_auth=_resolve_ia_auth(dry_run=dry_run),
        dry_run=dry_run,
    )

    start = time.time()
    exit_code = asyncio.run(run_sync(config))
    duration = time.time() - start

    sym = "[green]✓[/green]" if exit_code == 0 else "[red]✗[/red]"
    console.print(f"\n  {sym} Sync concluído em {_format_duration(duration)}\n")

    raise typer.Exit(code=exit_code)


@app.command()
def status(
    state_file: Path = typer.Option(
        _DEFAULT_STATE_FILE,
        "--backfill-state-file",
        help="Path to backfill progress JSON.",
    ),
) -> None:
    """Show per-tribunal backfill progress."""
    if not state_file.exists():
        console.print("[dim]No backfill state found.[/dim]")
        return

    bstate = SyncState.from_dict(json.loads(state_file.read_text()))
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
        streak_style = (
            "red" if prog.empty_streak > 30 else "yellow" if prog.empty_streak > 10 else ""
        )
        streak_text = (
            f"[{streak_style}]{prog.empty_streak}[/{streak_style}]"
            if streak_style
            else str(prog.empty_streak)
        )
        table.add_row(code, status_str, prog.cursor_date.isoformat(), streak_text, hit_str)

    console.print()
    console.print(table)
    console.print()


@app.command()
def reset(
    tribunal: str | None = typer.Option(
        None,
        help="Tribunal to reset. Omit to use --all.",
    ),
    *,
    all_tribunals: bool = typer.Option(
        False,
        "--all",
        help="Reset all stopped tribunals.",
    ),
    state_file: Path = typer.Option(
        _DEFAULT_STATE_FILE,
        "--backfill-state-file",
        help="Path to backfill progress JSON.",
    ),
) -> None:
    """Reset stopped tribunal(s) for re-scanning."""
    if not tribunal and not all_tribunals:
        console.print("[red]Error: provide --tribunal CODE or --all[/red]")
        raise typer.Exit(code=1)

    if not state_file.exists():
        console.print(f"[red]State file not found: {state_file}[/red]")
        raise typer.Exit(code=1)

    bstate = SyncState.from_dict(json.loads(state_file.read_text()))
    progress = bstate.get_all_progress()

    count = 0
    if tribunal:
        prog = progress.get(tribunal)
        if prog:
            prog.stopped = False
            prog.empty_streak = 0
            console.print(f"  [green]✓[/green] Reset {tribunal}")
            count = 1
        else:
            console.print(f"  [red]✗[/red] Tribunal {tribunal} not found in state.")
            console.print("  [dim]Nothing to reset.[/dim]")
    else:
        for code, prog in progress.items():
            if prog.stopped:
                prog.stopped = False
                prog.empty_streak = 0
                console.print(f"  [green]✓[/green] Reset {code}")
                count += 1

    if count > 0:
        state_file.write_text(json.dumps(bstate.to_dict(), indent=2))
        console.print(f"\n  {count} tribunal(s) reset.")
    elif tribunal:
        pass  # message already printed above
    else:
        console.print("  [dim]Nothing to reset.[/dim]")
