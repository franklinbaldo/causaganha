"""CLI command module for CausaGanha backfill pipeline."""

import asyncio
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from djen_backup.backfill import (
    load_backfill_state,
    save_backfill_state,
)


app = typer.Typer(
    help="Manage the DJEN backfill pipeline and Internet Archive uploads.",
    no_args_is_help=True,
)

console = Console()


# ── Data Types ──────────────────────────────────────────────


@dataclass
class StepResult:
    """Result of a single pipeline step."""

    name: str
    success: bool
    duration: float
    detail: str = ""
    error: str = ""


# ── Helpers ─────────────────────────────────────────────────



def _run_step(
    name: str,
    cmd: list[str],
    *,
    dry_run: bool = False,
    log_file: Path | None = None,
) -> StepResult:
    """Execute a pipeline step, capturing output."""
    if dry_run:
        console.print(f"  [dim]→ {' '.join(cmd)}[/dim]")
        return StepResult(name=name, success=True, duration=0.0, detail="dry-run")

    # backfill.py → commands/ → cli/ → causaganha/ → src/ → repo_root
    repo_root = str(Path(__file__).parent.parent.parent.parent.parent)
    env = {
        **os.environ,
        "PYTHONPATH": f"{repo_root}:{Path(repo_root) / 'src'}",
    }

    # Capture output to both log file and for error display
    fd, output_path = tempfile.mkstemp(prefix=f"cg-{name}-", suffix=".log")
    os.close(fd)

    env["GITHUB_OUTPUT"] = output_path

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            env=env,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        duration = time.time() - start

        # Append subprocess output to log file
        if log_file:
            with open(log_file, "a") as f:
                f.write(f"\n{'='*60}\n[{name}] {' '.join(cmd)}\n{'='*60}\n")
                if result.stdout:
                    f.write(result.stdout)
                if result.stderr:
                    f.write(result.stderr)

        # Parse GITHUB_OUTPUT for metadata
        outputs = {}
        out_file = Path(output_path)
        if out_file.exists():
            for line in out_file.read_text().splitlines():
                if "=" in line:
                    k, _, v = line.partition("=")
                    outputs[k.strip()] = v.strip()
            out_file.unlink(missing_ok=True)

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else f"exit code {result.returncode}"
            # Show last meaningful lines
            lines = [l for l in error_msg.splitlines() if l.strip()]
            short_error = "\n".join(lines[-5:]) if len(lines) > 5 else error_msg
            return StepResult(
                name=name, success=False, duration=duration, error=short_error
            )

        files_added = outputs.get("files_added")
        if files_added == "true":
            detail = "new files added"
        elif files_added == "false":
            detail = "no new files"
        else:
            detail = "done"
        return StepResult(name=name, success=True, duration=duration, detail=detail)

    except Exception as e:
        duration = time.time() - start
        return StepResult(name=name, success=False, duration=duration, error=str(e))
    finally:
        Path(output_path).unlink(missing_ok=True)


def _preflight_checks() -> None:
    """Check prerequisites before running the pipeline. Exits on failure."""
    errors: list[str] = []

    # Check IA credentials
    if not os.environ.get("IAS3_ACCESS_KEY") and not os.environ.get("IA_ACCESS_KEY"):
        errors.append("IAS3_ACCESS_KEY (ou IA_ACCESS_KEY) não definido no ambiente")
    if not os.environ.get("IAS3_SECRET_KEY") and not os.environ.get("IA_SECRET_KEY"):
        errors.append("IAS3_SECRET_KEY (ou IA_SECRET_KEY) não definido no ambiente")

    # Check scripts exist
    repo_root = Path(__file__).parent.parent.parent.parent.parent
    scripts_dir = repo_root / "scripts" / "pipeline"
    for script in ("collect.py", "consolidate.py", "embed.py"):
        if not (scripts_dir / script).exists():
            errors.append(f"Script não encontrado: {scripts_dir / script}")

    # Check uv is available
    import shutil
    if not shutil.which("uv"):
        errors.append("'uv' não encontrado no PATH")

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


def _format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m{secs:.0f}s"


# ── Commands ────────────────────────────────────────────────


@app.command()
def run(
    target_date: str = typer.Option(
        "",
        "--date",
        help="Data específica (YYYY-MM-DD). Default: próxima data do backfill.",
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
        5,
        help="Máximo de itens para coletar.",
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
) -> None:
    """Run the backfill pipeline locally."""
    from causaganha.cli import setup_logging

    # Load .env if present
    env_file = Path(__file__).parent.parent.parent.parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

    log_file = setup_logging(verbose=verbose)

    if not dry_run:
        _preflight_checks()

    # Resolve target date (only used if explicitly provided or for consolidate)
    pipeline_date = target_date  # empty string means "let djen-backup decide"

    # Show run configuration
    config_lines = [
        f"[bold]Data:[/bold]     {pipeline_date or 'auto (backfill scan)'}",
        f"[bold]Job:[/bold]      {job}",
        f"[bold]Tribunal:[/bold] {tribunal or 'todos'}",
        f"[bold]Items:[/bold]    {max_items}",
        f"[bold]Log:[/bold]      {log_file}",
    ]
    if dry_run:
        config_lines.append("[yellow bold]Modo:[/yellow bold]     dry-run (nenhuma ação será executada)")

    console.print()
    console.print(Panel(
        "\n".join(config_lines),
        title="[bold]Pipeline Run[/bold]",
        border_style="blue",
        padding=(1, 2),
    ))
    console.print()

    # backfill.py → commands/ → cli/ → causaganha/ → src/ → repo_root
    repo_root = str(Path(__file__).parent.parent.parent.parent.parent)
    scripts_dir = str(Path(repo_root) / "scripts" / "pipeline")

    results: list[StepResult] = []
    failed = False

    # Define steps based on job
    steps: list[tuple[str, list[str]]] = []

    if job in ("all", "collect"):
        cmd = ["uv", "run", "python", f"{scripts_dir}/collect.py"]
        if pipeline_date:
            cmd += ["--date", pipeline_date]
        # else: djen-backup scans backfill-state.json for missing dates
        if tribunal:
            cmd += ["--tribunal", tribunal]
        cmd += ["--max-items", str(max_items)]
        steps.append(("Collect", cmd))

    if job in ("all", "consolidate"):
        cmd = ["uv", "run", "python", f"{scripts_dir}/consolidate.py"]
        if pipeline_date:
            cmd += ["--date", pipeline_date]
        else:
            cmd += ["--backfill", "--force"]
        steps.append(("Consolidate", cmd))

    if job in ("all", "embed"):
        cmd = ["uv", "run", "python", f"{scripts_dir}/embed.py", "--deadline", "10m"]
        steps.append(("Embed", cmd))

    if job == "all":
        steps.append((
            "Catalog",
            ["uv", "run", "python", f"{repo_root}/scripts/generate_catalog.py", "--upload"],
        ))
        steps.append((
            "Dashboard",
            ["uv", "run", "python", f"{repo_root}/scripts/generate_dashboard_cache.py"],
        ))

    # Execute steps
    for step_name, cmd in steps:
        console.print(f"  ⏳ {step_name}...", end="")
        result = _run_step(step_name, cmd, dry_run=dry_run, log_file=log_file)
        results.append(result)

        if result.success:
            console.print(
                f"\r  [green]✓[/green] {step_name:<15s} "
                f"[dim]{_format_duration(result.duration)}[/dim]  "
                f"{result.detail}"
            )
        else:
            console.print(
                f"\r  [red]✗[/red] {step_name:<15s} "
                f"[dim]{_format_duration(result.duration)}[/dim]"
            )
            failed = True
            # Show error details
            if result.error:
                console.print(Panel(
                    result.error,
                    title=f"[red]Error in {step_name}[/red]",
                    border_style="red",
                    padding=(0, 1),
                ))
                console.print(f"  [dim]Detalhes completos em: {log_file}[/dim]")

            if not continue_on_error:
                break

    # Summary table
    console.print()
    table = Table(title="Pipeline Summary", border_style="dim")
    table.add_column("Step", style="bold")
    table.add_column("Time", justify="right")
    table.add_column("Result")

    total_time = sum(r.duration for r in results)
    for r in results:
        status = "[green]✓[/green]" if r.success else "[red]✗[/red]"
        detail = r.detail if r.success else r.error[:40]
        table.add_row(r.name, _format_duration(r.duration), f"{status} {detail}")

    table.add_section()
    overall = "[green]✓ Complete[/green]" if not failed else "[red]✗ Failed[/red]"
    table.add_row("[bold]Total[/bold]", f"[bold]{_format_duration(total_time)}[/bold]", overall)

    console.print(table)
    console.print(f"\n  [dim]Log salvo em: {log_file}[/dim]\n")

    if failed:
        raise typer.Exit(code=1)


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
