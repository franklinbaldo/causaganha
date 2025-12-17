
import asyncio
import json
import structlog
import typer
from datetime import date, timedelta

from causaganha.config import DB_PATH
from causaganha.storage.connection import get_connection
from causaganha.storage.schema import create_schema
from causaganha.storage.repository import IntimationRepository
from causaganha.api.client import PJeAPIClient
from causaganha.pipeline.collect import run_collection
from causaganha.pipeline.analyze import run_analysis
from causaganha.pipeline.archive import run_archive
from causaganha.pipeline.score import run_scoring
from causaganha.analysis.analyzer import DecisionAnalyzer
from causaganha.services.document import DocumentService
from causaganha.services.archive import create_archive_service

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

def _get_repository() -> IntimationRepository:
    """Helper to initialize repository and schema."""
    con = get_connection(DB_PATH)
    create_schema(con)
    return IntimationRepository(con)

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
    courts: str = typer.Option("TJRO", help="Comma-separated list of courts"),
) -> None:
    """Collect intimations from PJe."""
    logger.info("collect_command_start")

    async def _run():
        repository = _get_repository()
        client = PJeAPIClient()
        court_list = [c.strip() for c in courts.split(",")]

        try:
            await run_collection(repository, client, start_date, end_date, court_list)
        finally:
            await client.close()

    asyncio.run(_run())


@app.command()
def analyze(
    limit: int = typer.Option(10, help="Number of items to analyze"),
) -> None:
    """Analyze decisions using LLM."""
    logger.info("analyze_command_start")

    async def _run():
        repository = _get_repository()
        doc_service = DocumentService()
        analyzer = DecisionAnalyzer()

        await run_analysis(repository, doc_service, analyzer, limit=limit)

    asyncio.run(_run())

@app.command()
def archive(
    limit: int = typer.Option(10, help="Number of items to archive"),
    dry_run: bool = typer.Option(False, help="Perform a dry run without uploading"),
) -> None:
    """Download and archive diarios to Internet Archive."""
    logger.info("archive_start", limit=limit, dry_run=dry_run)

    async def _run():
        repository = _get_repository()
        doc_service = DocumentService()
        archive_service = create_archive_service()

        await run_archive(
            repository,
            doc_service,
            archive_service,
            limit=limit,
            dry_run=dry_run,
        )

    asyncio.run(_run())

@app.command()
def score(
    limit: int = typer.Option(100, help="Number of items to score"),
) -> None:
    """Calculate OpenSkill ratings for analyzed decisions."""
    logger.info("score_start", limit=limit)

    async def _run():
        await run_scoring(DB_PATH, limit=limit)

    asyncio.run(_run())

@app.command()
def pipeline(
    ctx: typer.Context,
    start_date: str = typer.Option(
        (date.today() - timedelta(days=1)).isoformat(),
        help="Start date (YYYY-MM-DD)",
    ),
    end_date: str = typer.Option(
        date.today().isoformat(),
        help="End date (YYYY-MM-DD)",
    ),
    courts: str = typer.Option("TJRO", help="Comma-separated list of courts"),
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
    opts = ctx.obj

    def echo(message: str) -> None:
        if not opts.get("quiet") and not opts.get("json"):
            typer.echo(message)

    def echo_json(data: dict) -> None:
        if opts.get("json"):
            typer.echo(json.dumps(data))

    async def _run():
        repository = _get_repository()
        client = PJeAPIClient()
        doc_service = DocumentService()
        archive_service = create_archive_service()
        analyzer = DecisionAnalyzer()
        court_list = [c.strip() for c in courts.split(",")]

        try:
            # Step 1: Collect
            if not skip_collect:
                echo("Step 1/4: Collecting intimations...")
                await run_collection(repository, client, start_date, end_date, court_list)
                echo("✓ Collection complete")
                echo_json({"step": 1, "name": "collect", "status": "complete"})
            else:
                echo("⊘ Skipping collection")

            # Step 2: Archive
            if not skip_archive:
                echo("Step 2/4: Archiving to Internet Archive...")
                await run_archive(
                    repository,
                    doc_service,
                    archive_service,
                    limit=archive_limit,
                    dry_run=False,
                )
                echo("✓ Archive complete")
                echo_json({"step": 2, "name": "archive", "status": "complete"})
            else:
                echo("⊘ Skipping archive")

            # Step 3: Analyze
            if not skip_analyze:
                echo("Step 3/4: Analyzing decisions...")
                await run_analysis(repository, doc_service, analyzer, limit=analyze_limit)
                echo("✓ Analysis complete")
                echo_json({"step": 3, "name": "analyze", "status": "complete"})
            else:
                echo("⊘ Skipping analysis")

            # Step 4: Score
            if not skip_score:
                echo("Step 4/4: Calculating ratings...")
                await run_scoring(DB_PATH, limit=score_limit)
                echo("✓ Scoring complete")
                echo_json({"step": 4, "name": "score", "status": "complete"})
            else:
                echo("⊘ Skipping scoring")

            echo("\n✓ Pipeline complete!")
            echo_json({"status": "complete", "final": True})

        finally:
            await client.close()

    asyncio.run(_run())

@app.command()
def db(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: init, status"),
) -> None:
    """Database management commands."""
    logger.info("db_command", action=action)
    opts = ctx.obj

    if action == "status":
        con = get_connection(DB_PATH)
        tables = con.list_tables()
        if opts.get("json"):
            typer.echo(json.dumps({"status": "connected", "tables": tables}))
        elif not opts.get("quiet"):
            typer.echo(f"Connected to DuckDB. Found tables: {tables}")

    elif action == "init":
        try:
            if not opts.get("quiet"):
                typer.echo("Initializing database schema...")
            con = get_connection(DB_PATH)
            create_schema(con)
            if not opts.get("quiet"):
                typer.echo("Schema created successfully.")
        except Exception as e:
            if not opts.get("quiet"):
                typer.echo(f"Initialization failed: {e}")
            raise typer.Exit(code=1)
    else:
        if not opts.get("quiet"):
            typer.echo(f"Unknown action: {action}")

@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON for scripting"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output for CI/CD"),
) -> None:
    """CausaGanha V2 CLI Entry Point.
    """
    ctx.obj = {"json": json_output, "quiet": quiet, "verbose": verbose}

    if quiet or json_output:
        # Define a logger that does nothing
        class NoOpLogger:
            def msg(self, *args, **kwargs): pass
            info = debug = warning = error = exception = critical = msg

        # Define a factory for it
        class NoOpLoggerFactory:
            def __call__(self, *args):
                return NoOpLogger()

        # Reconfigure structlog to use the no-op logger
        structlog.configure(logger_factory=NoOpLoggerFactory(), processors=[])
    elif verbose:
        # Reconfigure for verbose if needed, though dev renderer is already verbose-ish
        pass

if __name__ == "__main__":
    app()
