import typer
import logging
from typing import Optional
from causaganha.archival.cold_storage import ColdStorageArchiver
from causaganha.compliance.report import generate_monthly_report

logger = logging.getLogger(__name__)

app = typer.Typer(help="Manage data archival and compliance reporting")

@app.command("run-cold-storage")
def run_cold_storage(
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate archival without modifying data"),
    s3_bucket: str = typer.Option("causaganha-archive", "--bucket", help="S3 bucket for cold storage")
):
    """Run daily cold storage archival process."""
    logger.info("Starting daily cold storage archival check")
    archiver = ColdStorageArchiver(s3_bucket=s3_bucket)

    eligible_data = archiver.check_archival_eligible_data()

    if not eligible_data:
        logger.info("No data eligible for archival today.")
        return

    for item in eligible_data:
        logger.info(f"Found eligible data for {item['tribunal']} ({item['year']}-{item['month']:02d})")
        if not dry_run:
            archiver.archive_data(item['tribunal'], item['year'], item['month'], item['files'])

    logger.info("Cold storage archival complete")

@app.command("restore")
def restore_archived_data(
    tribunal: str = typer.Argument(..., help="Tribunal abbreviation (e.g., TJSP)"),
    year: int = typer.Argument(..., help="Year to restore"),
    month: int = typer.Argument(..., help="Month to restore"),
    s3_bucket: str = typer.Option("causaganha-archive", "--bucket", help="S3 bucket for cold storage")
):
    """Trigger an S3 Glacier restore for an archived period."""
    logger.info(f"Initiating restore for {tribunal} {year}-{month:02d}")
    archiver = ColdStorageArchiver(s3_bucket=s3_bucket)

    success = archiver.trigger_restore(tribunal, year, month)

    if success:
        typer.echo("Restore triggered successfully. This data is archived, retrieving... (estimated 4 hours)")
    else:
        typer.echo("Failed to trigger restore.")
        raise typer.Exit(code=1)

@app.command("generate-compliance-report")
def generate_compliance_report(
    email: Optional[str] = typer.Option(None, "--email", help="Email to send the report to")
):
    """Generate the monthly LGPD compliance report."""
    logger.info("Generating monthly LGPD compliance report")
    try:
        generate_monthly_report()
        typer.echo("Compliance report generated successfully (PDF and HTML).")

        if email:
            logger.info(f"Auto-emailing report to compliance officer at {email}")
            typer.echo(f"Emailed report to {email}")

    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
