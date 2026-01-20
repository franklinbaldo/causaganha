import asyncio
from datetime import date, timedelta
from typing import Any

import structlog
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from causaganha.config import settings
from causaganha.infrastructure.clients.archive import create_archive_service
from causaganha.infrastructure.clients.document import DocumentService

# Import V2 pipelines
from causaganha.v2.pipeline.collect import collect_metadata_for_all_courts
from causaganha.v2.pipeline.archive import archive_documents
from causaganha.v2.pipeline.analyze import analyze_pending_decisions
from causaganha.v2.pipeline.score import calculate_ratings
from causaganha.v2.storage.connection import get_connection

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

app = typer.Typer(
    name="causaganha",
    help="CausaGanha V2: Judicial Analysis Platform",
    no_args_is_help=True,
)

logger = structlog.get_logger()


def _handle_error(e: Exception, message: str) -> None:
    """Formats and prints a standardized error message."""
    typer.secho(f"❌ {message}", fg=typer.colors.RED, bold=True)
    error_details = f"{type(e).__name__}: {e}"
    lines = error_details.splitlines()
    max_line_length = max(len(line) for line in lines) if lines else 0

    typer.echo("\n" + "┌" + "─" * (max_line_length + 4) + "┐")
    for line in lines:
        typer.echo(f"│  {line.ljust(max_line_length)}  │")
    typer.echo("└" + "─" * (max_line_length + 4) + "┘" + "\n")
    raise typer.Exit(code=1)


@app.command()
def collect(
    days_back: int = typer.Option(7, help="Days back to fetch"),
    courts: str | None = typer.Option(
        None, help="Comma-separated list of courts. Defaults to config."
    ),
) -> None:
    """Collect intimations from PJe."""
    logger.info("collect_command_start")

    court_list = [c.strip() for c in courts.split(",")] if courts else settings.COURTS

    async def _run() -> None:
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Collecting intimations...", total=None)
                await collect_metadata_for_all_courts(court_list, days_back)
        except Exception as e:
            _handle_error(e, "Collection failed")

    asyncio.run(_run())


@app.command()
def archive(
    limit: int = typer.Option(10, help="Number of items to archive"),
    dry_run: bool = typer.Option(False, help="Perform a dry run without uploading"),
) -> None:
    """Download and archive documents to Internet Archive."""
    logger.info("archive_start", limit=limit, dry_run=dry_run)

    async def _run() -> None:
        doc_service = DocumentService()
        archive_service = create_archive_service()

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Archiving documents...", total=None)
                await archive_documents(
                    doc_service,
                    archive_service,
                    limit=limit,
                    dry_run=dry_run,
                )
        except Exception as e:
            _handle_error(e, "Archive failed")

    asyncio.run(_run())


@app.command()
def analyze(
    limit: int = typer.Option(10, help="Number of items to analyze"),
    max_batches: int | None = typer.Option(None, help="Max batches to process"),
    strategy: str = typer.Option(
        "hybrid",
        help="Analysis strategy: llm (expensive, accurate), rag (cheap, good), hybrid (optimal - default)",
    ),
    confidence_threshold: float = typer.Option(
        0.70,
        help="Confidence threshold for hybrid strategy (0.0-1.0). Below this triggers LLM fallback.",
    ),
) -> None:
    """Analyze decisions using AI (supports LLM, RAG, or hybrid strategies)."""
    logger.info("analyze_command_start", strategy=strategy)

    # Validate strategy
    valid_strategies = ["llm", "rag", "hybrid", "auto"]
    if strategy not in valid_strategies:
        typer.secho(
            f"❌ Invalid strategy '{strategy}'. Must be one of: {', '.join(valid_strategies)}",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    async def _run() -> None:
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task_desc = f"Analyzing decisions ({strategy} strategy)..."
                progress.add_task(description=task_desc, total=None)

                result = await analyze_pending_decisions(
                    batch_size=limit,
                    max_batches=max_batches,
                    strategy=strategy,
                    confidence_threshold=confidence_threshold,
                )

                # Display results
                typer.echo("\n✅ Analysis complete!")
                typer.echo(f"  Strategy: {result['strategy']}")
                typer.echo(f"  Analyzed: {result['analyzed']}")
                typer.echo(f"  Failed: {result['failed']}")

                if strategy in ["hybrid", "auto"]:
                    typer.echo(f"  RAG used: {result['rag_used']} ({result['rag_used']/result['analyzed']*100:.1f}%)")
                    typer.echo(f"  LLM used: {result['llm_used']} ({result['llm_used']/result['analyzed']*100:.1f}%)")

                typer.echo(f"  Total cost: ${result['total_cost']:.6f}")
                typer.echo(f"  Cost/decision: ${result['cost_per_decision']:.6f}")
                typer.echo(f"  Savings vs LLM: {result['savings_vs_llm_pct']:.1f}%")

        except Exception as e:
            _handle_error(e, "Analysis failed")

    asyncio.run(_run())


@app.command()
def score(
    limit: int = typer.Option(100, help="Number of items to score"),
) -> None:
    """Calculate OpenSkill ratings."""
    logger.info("score_start", limit=limit)

    async def _run() -> None:
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Calculating ratings...", total=None)
                await calculate_ratings(batch_size=limit)
        except Exception as e:
            _handle_error(e, "Scoring failed")

    asyncio.run(_run())


@app.command()
def pipeline(
    days_back: int = typer.Option(1, help="Days back to collect"),
    courts: str | None = typer.Option(
        None, help="Comma-separated list of courts. Defaults to config."
    ),
    analyze_limit: int = typer.Option(10, help="Number of items to analyze"),
    archive_limit: int = typer.Option(10, help="Number of items to archive"),
    score_limit: int = typer.Option(100, help="Number of items to score"),
    skip_collect: bool = typer.Option(False, help="Skip collection step"),
    skip_archive: bool = typer.Option(False, help="Skip archive step"),
    skip_analyze: bool = typer.Option(False, help="Skip analysis step"),
    skip_score: bool = typer.Option(False, help="Skip scoring step"),
) -> None:
    """Run the complete pipeline: collect → archive → analyze → score."""
    logger.info("pipeline_start")

    court_list = [c.strip() for c in courts.split(",")] if courts else settings.COURTS

    async def _run() -> None:
        doc_service = DocumentService()
        archive_service = create_archive_service()

        try:
            # Step 1: Collect
            if not skip_collect:
                typer.echo("Step 1/4: Collecting intimations...")
                await collect_metadata_for_all_courts(court_list, days_back)
                typer.echo("✓ Collection complete")
            else:
                typer.echo("⊘ Skipping collection")

            # Step 2: Archive
            if not skip_archive:
                typer.echo("Step 2/4: Archiving to Internet Archive...")
                await archive_documents(
                    doc_service,
                    archive_service,
                    limit=archive_limit,
                )
                typer.echo("✓ Archive complete")
            else:
                typer.echo("⊘ Skipping archive")

            # Step 3: Analyze
            if not skip_analyze:
                typer.echo("Step 3/4: Analyzing decisions...")
                await analyze_pending_decisions(batch_size=analyze_limit)
                typer.echo("✓ Analysis complete")
            else:
                typer.echo("⊘ Skipping analysis")

            # Step 4: Score
            if not skip_score:
                typer.echo("Step 4/4: Calculating ratings...")
                await calculate_ratings(batch_size=score_limit)
                typer.echo("✓ Scoring complete")
            else:
                typer.echo("⊘ Skipping scoring")

            typer.echo("\n✓ Pipeline complete!")

        except Exception as e:
            _handle_error(e, "Pipeline failed")

    asyncio.run(_run())


@app.command()
def db(action: str = typer.Argument(..., help="Action: init, status, migrate")) -> None:
    """Database management commands."""
    logger.info("db_command", action=action)
    if action == "status":
        con = get_connection()
        tables = con.list_tables()
        typer.echo(f"Connected to DuckDB. Found tables: {tables}")
    elif action == "init":
        try:
            typer.echo("Initializing database schema...")
            con = get_connection()
            # Schema is auto-initialized by get_connection in V2
            typer.echo("✅ Schema initialized successfully.")
        except Exception as e:
            _handle_error(e, "Initialization failed")
    elif action == "migrate":
        try:
            typer.echo("Running migrations for RAG support...")
            con = get_connection()
            import os

            migration_file = "src/causaganha/v2/storage/migrations/001_add_rag_support.sql"
            if os.path.exists(migration_file):
                with open(migration_file) as f:
                    sql = f.read()
                    # Split by semicolon and execute each statement
                    for statement in sql.split(";"):
                        if statement.strip():
                            try:
                                con.con.execute(statement)
                            except Exception as e:
                                # Ignore errors for columns that already exist
                                if "already exists" not in str(e).lower():
                                    typer.echo(f"Warning: {e}")

                typer.echo("✅ Migrations applied successfully.")
            else:
                typer.echo(f"❌ Migration file not found: {migration_file}")
        except Exception as e:
            _handle_error(e, "Migration failed")
    else:
        typer.echo(f"Unknown action: {action}")


# Ground truth management commands
groundtruth_app = typer.Typer(help="Ground truth management for RAG")
app.add_typer(groundtruth_app, name="groundtruth")


@groundtruth_app.command("status")
def groundtruth_status() -> None:
    """Check ground truth vector store status."""
    try:
        from causaganha.v2.analysis.vector_store import VectorStore

        store = VectorStore()
        tables = store.list_tables()

        typer.echo("Vector Store Status:")
        typer.echo(f"  Location: {store.db_path}")
        typer.echo(f"  Tables: {len(tables)}")

        if "ground_truth" in tables:
            info = store.get_table_info("ground_truth")
            typer.echo(f"\n✅ Ground truth table exists:")
            typer.echo(f"  Records: {info['num_records']}")
        else:
            typer.echo("\n❌ Ground truth table not found.")
            typer.echo("Run 'causaganha groundtruth init' to create it.")

    except Exception as e:
        _handle_error(e, "Failed to check ground truth status")


@groundtruth_app.command("info")
def groundtruth_info() -> None:
    """Show detailed ground truth information."""
    try:
        con = get_connection()

        # Check if we have high-confidence analyses to use as ground truth
        query = """
            SELECT
                analysis_method,
                COUNT(*) as total,
                AVG(confidence_score) as avg_confidence,
                COUNT(DISTINCT outcome) as unique_outcomes
            FROM decision_analysis
            WHERE confidence_score >= 0.90
            GROUP BY analysis_method
        """

        result = con.con.execute(query).fetchall()

        typer.echo("High-Confidence Analyses (≥90% confidence):")
        typer.echo("Can be used as ground truth for RAG\n")

        if result:
            for row in result:
                method, total, avg_conf, outcomes = row
                typer.echo(f"  {method}: {total} decisions (avg confidence: {avg_conf:.2%})")
        else:
            typer.echo("  No high-confidence analyses found yet.")
            typer.echo("  Run some LLM analyses first to build ground truth.")

    except Exception as e:
        _handle_error(e, "Failed to get ground truth info")


if __name__ == "__main__":
    app()
