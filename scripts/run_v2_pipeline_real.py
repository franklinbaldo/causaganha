#!/usr/bin/env python3
"""
Run the full V2 pipeline with real data.

Stages:
1. Collection (API -> DuckDB)
2. Analysis (LLM/RAG -> DuckDB)
3. Scoring (OpenSkill -> DuckDB)
"""

import asyncio
import sys
from pathlib import Path
import structlog
import typer
from rich.console import Console
from rich.table import Table

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from causaganha.v2.pipeline.collect import collect_metadata_for_court
from causaganha.v2.pipeline.analyze import analyze_pending_decisions
from causaganha.v2.pipeline.score import calculate_ratings
from causaganha.v2.storage.connection import get_connection

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()
console = Console()
app = typer.Typer()


@app.command()
def main(
    court: str = typer.Argument(..., help="Court acronym (e.g. TJRO)"),
    days: int = typer.Option(1, help="Days back to collect"),
    analyze_batch: int = typer.Option(10, help="Batch size for analysis"),
    max_analyze_batches: int = typer.Option(None, help="Max analysis batches (None=all)"),
    score_batch: int = typer.Option(100, help="Batch size for scoring"),
    db_path: str = typer.Option("data/causaganha.duckdb", help="Path to DuckDB file"),
):
    """Run the full V2 pipeline."""
    asyncio.run(run_pipeline(court, days, analyze_batch, max_analyze_batches, score_batch, db_path))


async def run_pipeline(
    court: str,
    days: int,
    analyze_batch: int,
    max_analyze_batches: int | None,
    score_batch: int,
    db_path: str,
):
    console.print(f"[bold green]Starting V2 Pipeline for {court}[/bold green]")

    # Ensure DB connection is initialized with the correct path
    # We need to set the global connection or just ensure subsequent calls use the same default if path is default
    # The pipeline functions call get_connection() with default path.
    # If we want to support custom db_path, we might need to patch get_connection or set the singleton.
    # For now, let's assume default path or that we only support what get_connection supports.
    # The `get_connection` function uses a global singleton. If we initialize it here, it might be used?
    # Actually, `get_connection` takes `db_path`. But pipeline functions don't take `db_path`.
    # Pipeline functions call `get_connection()` without arguments.
    # So `db_path` argument here is only useful if we modify `get_connection` behavior.
    # Let's override the singleton.

    import causaganha.v2.storage.connection
    causaganha.v2.storage.connection._connection = None # Reset
    # Initialize with provided path
    con = get_connection(db_path)

    # STAGE 1: COLLECTION
    console.print("\n[bold]Stage 1: Collection[/bold]")
    try:
        collect_result = await collect_metadata_for_court(court, days_back=days)
        print_result("Collection", collect_result)

        if collect_result["status"] != "success":
            console.print("[bold red]Collection failed. Stopping.[/bold red]")
            return
    except Exception as e:
        console.print(f"[bold red]Collection error: {e}[/bold red]")
        return

    # STAGE 2: ANALYSIS
    console.print("\n[bold]Stage 2: Analysis[/bold]")
    try:
        analyze_result = await analyze_pending_decisions(
            batch_size=analyze_batch,
            max_batches=max_analyze_batches
        )
        print_result("Analysis", analyze_result)

        if analyze_result["status"] != "success":
            console.print("[bold red]Analysis failed or partial. Continuing to scoring...[/bold red]")
    except Exception as e:
        console.print(f"[bold red]Analysis error: {e}[/bold red]")
        # We can continue if analysis failed completely but there are previous analyses?
        pass

    # STAGE 3: SCORING
    console.print("\n[bold]Stage 3: Scoring[/bold]")
    try:
        score_result = await calculate_ratings(batch_size=score_batch)
        print_result("Scoring", score_result)
    except Exception as e:
        console.print(f"[bold red]Scoring error: {e}[/bold red]")

    console.print("\n[bold green]Pipeline Completed[/bold green]")


def print_result(stage: str, result: dict):
    table = Table(title=f"{stage} Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    for key, value in result.items():
        table.add_row(str(key), str(value))

    console.print(table)


if __name__ == "__main__":
    app()
