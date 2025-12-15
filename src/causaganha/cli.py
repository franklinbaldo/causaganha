
import asyncio
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
from causaganha.analysis.analyzer import DecisionAnalyzer
from causaganha.services.document import DocumentService

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
def archive() -> None:
    """Download and archive diarios.
    """
    logger.info("archive_start", version="v2")
    typer.echo("Archive command not yet implemented in V2.")
    # TODO: Connect to src.causaganha.pipeline.collect

@app.command()
def db(action: str = typer.Argument(..., help="Action: init, status")) -> None:
    """Database management commands.
    """
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
             typer.echo("Schema created successfully.")
         except Exception as e:
             typer.echo(f"Initialization failed: {e}")
             raise typer.Exit(code=1)
    else:
        typer.echo(f"Unknown action: {action}")

@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """CausaGanha V2 CLI Entry Point.
    """
    if verbose:
        # Reconfigure for verbose if needed, though dev renderer is already verbose-ish
        pass

if __name__ == "__main__":
    app()
