"""CLI command module for CausaGanha backfill."""

from pathlib import Path

import typer

from djen_backup.backfill import (
    load_backfill_state,
    save_backfill_state,
)


app = typer.Typer(
    help="Manage the DJEN backfill pipeline and Internet Archive uploads.",
    no_args_is_help=True,
)


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
        typer.echo("No backfill state found.")
        return

    running = sum(1 for p in progress.values() if not p.stopped)
    stopped = sum(1 for p in progress.values() if p.stopped)
    typer.echo(f"Tribunals: {len(progress)} total, {running} running, {stopped} stopped\n")

    for code in sorted(progress):
        prog = progress[code]
        flag = "STOPPED" if prog.stopped else "running"
        hit_str = prog.last_hit_date.isoformat() if prog.last_hit_date else "never"
        typer.echo(
            f"  {code:12s}  {flag:8s}  cursor={prog.cursor_date.isoformat()}"
            f"  streak={prog.empty_streak:3d}  last_hit={hit_str}"
        )


@app.command()
def reset(
    tribunal: str | None = typer.Option(
        None,
        help="Reset a specific tribunal. Omit for --all.",
    ),
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
    import asyncio

    if not tribunal and not all:
        typer.echo("Error: provide --tribunal CODE or --all", err=True)
        raise typer.Exit(code=1)

    bstate = load_backfill_state(backfill_state_file)
    progress = bstate.get_all_progress()

    async def _reset() -> int:
        count = 0
        if tribunal:
            if await bstate.reset_tribunal(tribunal):
                typer.echo(f"Reset {tribunal}")
                count = 1
            else:
                typer.echo(f"Tribunal {tribunal} not found in state.", err=True)
        else:
            for code, prog in progress.items():
                if prog.stopped:
                    await bstate.reset_tribunal(code)
                    typer.echo(f"Reset {code}")
                    count += 1
        return count

    count = asyncio.run(_reset())
    if count > 0:
        save_backfill_state(bstate, backfill_state_file)
        typer.echo(f"\n{count} tribunal(s) reset.")
    else:
        typer.echo("Nothing to reset.")
