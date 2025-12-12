
import structlog
import typer


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

@app.command()
def archive():
    """Download and archive diarios.
    """
    logger.info("archive_start", version="v2")
    typer.echo("Archive command not yet implemented in V2.")
    # TODO: Connect to src.causaganha.pipeline.collect

@app.command()
def analyze():
    """Analyze decisions using LLM.
    """
    logger.info("analyze_start", version="v2")
    typer.echo("Analyze command not yet implemented in V2.")
    # TODO: Connect to src.causaganha.pipeline.analyze

@app.command()
def db(action: str = typer.Argument(..., help="Action: init, status")):
    """Database management commands.
    """
    logger.info("db_command", action=action)
    if action == "status":
         typer.echo("Checking database status... (TODO)")
    elif action == "init":
         typer.echo("Initializing database... (TODO)")
    else:
        typer.echo(f"Unknown action: {action}")

@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """CausaGanha V2 CLI Entry Point.
    """
    if verbose:
        # Reconfigure for verbose if needed, though dev renderer is already verbose-ish
        pass

if __name__ == "__main__":
    app()
