"""CLI command module for the DJEN backfill pipeline."""

from __future__ import annotations

import asyncio
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
from djen_backup.engine import SyncConfig, run_sync
from djen_backup.manifest import SyncManifest


app = typer.Typer(
    help="Manage the DJEN backfill pipeline and Internet Archive uploads.",
    no_args_is_help=True,
)

console = Console()

_DEFAULT_MANIFEST_FILE = Path("data/sync-manifest.csv")


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
def run(  # noqa: PLR0913
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
    manifest_file: Path = typer.Option(
        _DEFAULT_MANIFEST_FILE,
        "--manifest-file",
        help="Path ao arquivo CSV do manifesto.",
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
        f"[bold]Manifest:[/bold] {manifest_file}",
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
        manifest_file=manifest_file,
        djen_proxy_url=_resolve_djen_url(
            use_proxy=use_proxy
            or os.environ.get("DJEN_USE_PROXY", "").lower() in ("1", "true", "yes", "on")
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
    manifest_file: Path = typer.Option(
        _DEFAULT_MANIFEST_FILE,
        "--manifest-file",
        help="Path to manifest CSV.",
    ),
) -> None:
    """Show manifest summary."""
    manifest = SyncManifest()
    loaded = manifest.load_from_disk(manifest_file)
    if not loaded:
        console.print("[dim]No manifest found.[/dim]")
        return

    counts = manifest.counts()

    table = Table(title="Manifest Summary", border_style="dim")
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("Total entries", str(counts.total))
    table.add_row("[green]Uploaded[/green]", str(counts.uploaded))
    table.add_row("[yellow]Available[/yellow]", str(counts.available))
    table.add_row("[dim]Absent[/dim]", str(counts.absent))
    table.add_row("[red]Unknown[/red]", str(counts.unknown))

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
        help="Reset all entries.",
    ),
    manifest_file: Path = typer.Option(
        _DEFAULT_MANIFEST_FILE,
        "--manifest-file",
        help="Path to manifest CSV.",
    ),
) -> None:
    """Reset manifest entries for re-scanning."""
    if not tribunal and not all_tribunals:
        console.print("[red]Error: provide --tribunal CODE or --all[/red]")
        raise typer.Exit(code=1)

    manifest = SyncManifest()
    manifest.load_from_disk(manifest_file)

    count = 0
    for entry in manifest._entries.values():
        if all_tribunals or (tribunal and entry.tribunal == tribunal.upper()):
            entry.ia_status = ""
            entry.djen_status = ""
            entry.updated_at = ""
            count += 1

    if count > 0:
        manifest.save_to_disk(manifest_file)
        console.print(f"  [green]✓[/green] Reset {count} entries.")
    else:
        console.print("  [dim]Nothing to reset.[/dim]")
