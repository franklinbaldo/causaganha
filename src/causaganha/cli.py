
import asyncio
import json
from datetime import date, timedelta

import structlog
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from causaganha.analysis.analyzer import DecisionAnalyzer
from causaganha.config import DB_PATH, settings
from causaganha.integrations.pje.client import PJeAPIClient
from causaganha.pipeline.analyze import run_analysis
from causaganha.pipeline.archive import run_archive
from causaganha.schemas.orchestrator import ParquetSchema
from causaganha.pipeline.collect import run_collection
from causaganha.pipeline.score import run_scoring
from causaganha.services.archive import create_archive_service
from causaganha.services.document import DocumentService
from causaganha.storage.connection import get_connection
from causaganha.storage.repositories.analysis import AnalysisRepository
from causaganha.storage.repositories.intimation import IntimationRepository
from causaganha.storage.repositories.lawyer import LawyerRatingRepository
from causaganha.storage.schema import create_schema


# Configure basic logging (can be enhanced later)
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

    # Indent the error details for readability
    error_details = f"{type(e).__name__}: {e}"
    # handle multiline errors
    lines = error_details.splitlines()
    max_line_length = max(len(line) for line in lines) if lines else 0

    typer.echo("\n" + "┌" + "─" * (max_line_length + 4) + "┐")
    for line in lines:
        typer.echo(f"│  {line.ljust(max_line_length)}  │")
    typer.echo("└" + "─" * (max_line_length + 4) + "┘" + "\n")

    typer.secho("💡 Actionable Suggestions:", fg=typer.colors.YELLOW)
    typer.echo("- Check that you have write permissions for the 'data/' directory.")
    typer.echo("- Ensure all dependencies are correctly installed with 'uv sync --dev'.")
    typer.echo("- For more detailed logs, run the command with the --verbose flag.")
    raise typer.Exit(code=1)


def _get_repositories() -> tuple[IntimationRepository, AnalysisRepository, LawyerRatingRepository]:
    """Helper to initialize repositories and schema."""
    con = get_connection(DB_PATH)
    return (
        IntimationRepository(con),
        AnalysisRepository(con),
        LawyerRatingRepository(con),
    )

@app.command()
def collect(
    start_date: str = typer.Option(
        (date.today() - timedelta(days=1)).isoformat(),
        help="Start date (YYYY-MM-DD)",
    ),
    end_date: str = typer.Option(
        date.today().isoformat(),
        help="End date (YYYY-MM-DD)",
    ),
    courts: str | None = typer.Option(None, help="Comma-separated list of courts. Defaults to config."),
) -> None:
    """Collect intimations from PJe."""
    logger.info("collect_command_start")

    async def _run() -> None:
        repository, _, _ = _get_repositories()
        client = PJeAPIClient()
        court_list = [c.strip() for c in courts.split(",")] if courts else settings.COURTS

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Coletando intimações...", total=None)
                await run_collection(
                    repository, client, start_date, end_date, court_list,
                )
        finally:
            await client.close()

    try:
        asyncio.run(_run())
    except Exception as e:
        _handle_error(e, "Collection failed")


@app.command()
def analyze(
    limit: int = typer.Option(10, help="Number of items to analyze"),
) -> None:
    """Analyze decisions using LLM."""
    logger.info("analyze_command_start")

    async def _run() -> None:
        repository, analysis_repo, _ = _get_repositories()
        doc_service = DocumentService()
        analyzer = DecisionAnalyzer()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Analisando intimações...", total=None)
            await run_analysis(
                repository,
                analysis_repo,
                doc_service,
                analyzer,
                limit=limit,
            )

    try:
        asyncio.run(_run())
    except Exception as e:
        _handle_error(e, "Analysis failed")


@app.command()
def archive(
    limit: int = typer.Option(10, help="Number of items to archive"),
    dry_run: bool = typer.Option(False, help="Perform a dry run without uploading"),
) -> None:
    """Download and archive diarios to Internet Archive."""
    logger.info("archive_start", limit=limit, dry_run=dry_run)

    async def _run() -> None:
        repository, _, _ = _get_repositories()
        doc_service = DocumentService()
        archive_service = create_archive_service()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Arquivando decisões...", total=None)
            await run_archive(
                repository,
                doc_service,
                archive_service,
                limit=limit,
                dry_run=dry_run,
            )

    try:
        asyncio.run(_run())
    except Exception as e:
        _handle_error(e, "Archive failed")


@app.command()
def score(
    limit: int = typer.Option(100, help="Number of items to score"),
) -> None:
    """Calculate OpenSkill ratings for analyzed decisions."""
    logger.info("score_start", limit=limit)

    async def _run() -> None:
        try:
            _, analysis_repo, rating_repo = _get_repositories()
            await run_scoring(analysis_repo, rating_repo, limit=limit)
        except Exception as e:
            _handle_error(e, "Scoring failed")

    asyncio.run(_run())

@app.command()
def pipeline(
    start_date: str = typer.Option(
        (date.today() - timedelta(days=1)).isoformat(),
        help="Start date (YYYY-MM-DD)",
    ),
    end_date: str = typer.Option(
        date.today().isoformat(),
        help="End date (YYYY-MM-DD)",
    ),
    courts: str | None = typer.Option(None, help="Comma-separated list of courts. Defaults to config."),
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

    async def _run() -> None:
        repository, analysis_repo, rating_repo = _get_repositories()
        client = PJeAPIClient()
        doc_service = DocumentService()
        archive_service = create_archive_service()
        analyzer = DecisionAnalyzer()

        court_list = [c.strip() for c in courts.split(",")] if courts else settings.COURTS

        try:
            # Step 1: Collect
            if not skip_collect:
                typer.echo("Step 1/4: Collecting intimations...")
                await run_collection(repository, client, start_date, end_date, court_list)
                typer.echo("✓ Collection complete")
            else:
                typer.echo("⊘ Skipping collection")

            # Step 2: Archive
            if not skip_archive:
                typer.echo("Step 2/4: Archiving to Internet Archive...")
                await run_archive(
                    repository,
                    doc_service,
                    archive_service,
                    limit=archive_limit,
                    dry_run=False,
                )
                typer.echo("✓ Archive complete")
            else:
                typer.echo("⊘ Skipping archive")

            # Step 3: Analyze
            if not skip_analyze:
                typer.echo("Step 3/4: Analyzing decisions...")
                await run_analysis(
                    repository,
                    analysis_repo,
                    doc_service,
                    analyzer,
                    limit=analyze_limit,
                )
                typer.echo("✓ Analysis complete")
            else:
                typer.echo("⊘ Skipping analysis")

            # Step 4: Score
            if not skip_score:
                typer.echo("Step 4/4: Calculating ratings...")
                await run_scoring(analysis_repo, rating_repo, limit=score_limit)
                typer.echo("✓ Scoring complete")
            else:
                typer.echo("⊘ Skipping scoring")

            typer.echo("\n✓ Pipeline complete!")
        except Exception as e:
            _handle_error(e, "Pipeline failed")
        finally:
            await client.close()

    asyncio.run(_run())

@app.command()
def db(action: str = typer.Argument(..., help="Action: init, status")) -> None:
    """Database management commands."""
    logger.info("db_command", action=action)
    if action == "status":
         con = get_connection(DB_PATH)
         tables = con.list_tables()
         typer.echo(f"Connected to DuckDB. Found tables: {tables}")
    elif action == "init":
         try:
             typer.echo("Initializing database schema...")
             con = get_connection(DB_PATH)
             create_schema(con)
             typer.echo("✅ Schema created successfully.")
         except Exception as e:
             _handle_error(e, "Initialization failed")
    else:
        typer.echo(f"Unknown action: {action}")


manifest_app = typer.Typer(name="manifest", help="Manage and export data manifests.")

@manifest_app.command("export")
def manifest_export(
    limit: int = typer.Option(100, help="Number of items to export"),
) -> None:
    """Export intimations metadata as a JSON manifest."""
    # Suppress logging for this command so it outputs only pure JSON
    structlog.configure(logger_factory=structlog.ReturnLogger)

    repository, _, _ = _get_repositories()

    async def _export() -> None:
        items = await repository.get_all_intimations(limit=limit)
        output_items = []
        for item in items:
            # Convert date string to date object if it exists
            decision_date = None
            if item.get("data_disponibilizacao"):
                try:
                    decision_date = date.fromisoformat(item["data_disponibilizacao"])
                except (ValueError, TypeError):
                    pass  # Keep as None if parsing fails

            schema = ParquetSchema(
                intimation_id=item.get("id"),
                process_number=item.get("numero_processo"),
                tribunal=item.get("sigla_tribunal"),
                decision_date=decision_date,
                download_url=item.get("link"),
                needs_download=item.get("needs_download", True),
                ia_url=item.get("ia_url"),
            )
            output_items.append(schema.model_dump(mode="json"))

        typer.echo(json.dumps(output_items, indent=2))

    asyncio.run(_export())

app.add_typer(manifest_app)


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """CausaGanha V2 CLI Entry Point."""
    if verbose:
        # Reconfigure for verbose if needed, though dev renderer is already verbose-ish
        pass

if __name__ == "__main__":
    app()
