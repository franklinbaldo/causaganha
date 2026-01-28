import asyncio
import os

import structlog
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

# from causaganha.analysis.ground_truth import GroundTruthManager
from causaganha.clients.archive import create_archive_service
from causaganha.config import settings

# from causaganha.clients.document import DocumentService
from causaganha.pipeline.analyze import analyze_pending_decisions
from causaganha.pipeline.analyze_parquet import analyze_from_parquet

# from causaganha.pipeline.archive import archive_documents
from causaganha.pipeline.collect import collect_metadata_for_all_courts
from causaganha.pipeline.score import calculate_ratings
from causaganha.storage.connection import get_connection


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

groundtruth_app = typer.Typer(name="groundtruth", help="Manage ground truth vector store")
app.add_typer(groundtruth_app, name="groundtruth")


@groundtruth_app.command("init")
def groundtruth_init(
    overwrite: bool = typer.Option(False, help="Overwrite existing table"),
) -> None:
    """Initialize the ground truth vector store to ready state."""
    from causaganha.analysis.ground_truth import GroundTruthManager

    manager = GroundTruthManager()
    manager.init_store(overwrite=overwrite)
    typer.echo("✅ Ground truth vector store initialized")


@groundtruth_app.command("sync")
def groundtruth_sync(
    min_confidence: float = typer.Option(0.9, help="Minimum confidence score"),
    limit: int = typer.Option(100, help="Max records to sync"),
) -> None:
    """Sync high-confidence analyses from DuckDB."""

    async def _run() -> None:
        try:
            from causaganha.analysis.ground_truth import GroundTruthManager

            manager = GroundTruthManager()
            result = await manager.sync(min_confidence=min_confidence, limit=limit)
            typer.echo(f"✅ Sync complete! Added {result['synced']} new examples")
        except Exception as e:
            _handle_error(e, "Sync failed")

    asyncio.run(_run())


@groundtruth_app.command("search")
def groundtruth_search(
    query: str = typer.Argument(..., help="Text to search for"),
    k: int = typer.Option(5, help="Number of results"),
) -> None:
    """Search for matching examples."""

    async def _run() -> None:
        try:
            from causaganha.analysis.ground_truth import GroundTruthManager

            manager = GroundTruthManager()
            results = await manager.search(query, k=k)
            for res in results:
                typer.echo(f"Outcome: {res['outcome']}")
                typer.echo(f"Text: {res['text'][:200]}...")
                typer.echo("---")
        except Exception as e:
            _handle_error(e, "Search failed")

    asyncio.run(_run())


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
        None,
        help="Comma-separated list of courts. Defaults to config.",
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
            # typer.echo("⊘ Collection currently disabled (switching to DJEN scraper).")
        except Exception as e:
            _handle_error(e, "Collection failed")

    asyncio.run(_run())


# @app.command()
# def archive(
#     limit: int = typer.Option(10, help="Number of items to archive"),
#     dry_run: bool = typer.Option(False, help="Perform a dry run without uploading"),
# ) -> None:
#     """Download and archive documents to Internet Archive."""
#     logger.info("archive_start", limit=limit, dry_run=dry_run)
#
#     async def _run() -> None:
#         doc_service = DocumentService()
#         archive_service = create_archive_service()
#
#         try:
#             with Progress(
#                 SpinnerColumn(),
#                 TextColumn("[progress.description]{task.description}"),
#                 transient=True,
#             ) as progress:
#                 progress.add_task(description="Archiving documents...", total=None)
#                 await archive_documents(
#                     doc_service,
#                     archive_service,
#                     limit=limit,
#                     dry_run=dry_run,
#                 )
#         except Exception as e:
#             _handle_error(e, "Archive failed")
#
#     asyncio.run(_run())


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
                    typer.echo(
                        f"  RAG used: {result['rag_used']} ({result['rag_used']/result['analyzed']*100:.1f}%)",
                    )
                    typer.echo(
                        f"  LLM used: {result['llm_used']} ({result['llm_used']/result['analyzed']*100:.1f}%)",
                    )

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


# @app.command()
# def pipeline(
#     days_back: int = typer.Option(1, help="Days back to collect"),
#     courts: str | None = typer.Option(
#         None,
#         help="Comma-separated list of courts. Defaults to config.",
#     ),
#     analyze_limit: int = typer.Option(10, help="Number of items to analyze"),
#     archive_limit: int = typer.Option(10, help="Number of items to archive"),
#     score_limit: int = typer.Option(100, help="Number of items to score"),
#     skip_collect: bool = typer.Option(False, help="Skip collection step"),
#     skip_archive: bool = typer.Option(False, help="Skip archive step"),
#     skip_analyze: bool = typer.Option(False, help="Skip analysis step"),
#     skip_score: bool = typer.Option(False, help="Skip scoring step"),
# ) -> None:
#     """Run the complete pipeline: collect → archive → analyze → score."""
#     logger.info("pipeline_start")
#
#     court_list = [c.strip() for c in courts.split(",")] if courts else settings.COURTS
#
#     async def _run() -> None:
#         doc_service = DocumentService()
#         archive_service = create_archive_service()
#
#         try:
#             # Step 1: Collect
#             if not skip_collect:
#                 typer.echo("Step 1/4: Collecting intimations (SKIPPED - Switching to DJEN)...")
#                 # await collect_metadata_for_all_courts(court_list, days_back)
#                 # typer.echo("✓ Collection complete")
#             else:
#                 typer.echo("⊘ Skipping collection")
#
#             # Step 2: Archive
#             if not skip_archive:
#                 typer.echo("Step 2/4: Archiving to Internet Archive...")
#                 await archive_documents(
#                     doc_service,
#                     archive_service,
#                     limit=archive_limit,
#                 )
#                 typer.echo("✓ Archive complete")
#             else:
#                 typer.echo("⊘ Skipping archive")
#
#             # Step 3: Analyze
#             if not skip_analyze:
#                 typer.echo("Step 3/4: Analyzing decisions...")
#                 await analyze_pending_decisions(batch_size=analyze_limit)
#                 typer.echo("✓ Analysis complete")
#             else:
#                 typer.echo("⊘ Skipping analysis")
#
#             # Step 4: Score
#             if not skip_score:
#                 typer.echo("Step 4/4: Calculating ratings...")
#                 await calculate_ratings(batch_size=score_limit)
#                 typer.echo("✓ Scoring complete")
#             else:
#                 typer.echo("⊘ Skipping scoring")
#
#             typer.echo("\n✓ Pipeline complete!")
#
#         except Exception as e:
#             _handle_error(e, "Pipeline failed")
#
#     asyncio.run(_run())


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
            typer.echo("Running migrations...")
            from causaganha.storage.migrations import migration_status, run_migrations

            con = get_connection()

            # Show current status
            status = migration_status(con)
            typer.echo(f"  Current: {status['applied']}/{status['total']} applied")

            if status["pending"] == 0:
                typer.echo("✅ All migrations already applied.")
                return

            typer.echo(f"  Pending: {status['pending']} migrations")

            # Run pending migrations
            applied = run_migrations(con)

            if applied:
                typer.echo(f"✅ Applied {len(applied)} migrations:")
                for name in applied:
                    typer.echo(f"    - {name}")
            else:
                typer.echo("✅ No migrations to apply.")
        except Exception as e:
            _handle_error(e, "Migration failed")
    else:
        typer.echo(f"Unknown action: {action}")


@app.command()
def export_parquet(
    date: str | None = typer.Option(
        None,
        help="Date to export (YYYY-MM-DD), defaults to yesterday",
    ),
    tribunal: str | None = typer.Option(None, help="Specific tribunal to export (optional)"),
    backfill: bool = typer.Option(False, help="Backfill mode"),
    start_date: str | None = typer.Option(None, help="Start date for backfill (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(None, help="End date for backfill (YYYY-MM-DD)"),
    no_cleanup: bool = typer.Option(False, help="Keep local Parquet files after upload"),
) -> None:
    """Export analyzed decisions to Parquet and upload to Internet Archive."""
    logger.info("export_parquet_command_start", date=date, tribunal=tribunal, backfill=backfill)

    async def _run() -> None:
        try:
            from causaganha.pipeline.export_orchestrator import ExportOrchestrator
            from causaganha.pipeline.ia_upload import InternetArchiveUploader, UploadConfig
            from causaganha.pipeline.parquet_export import ExportConfig, ParquetExporter

            # Initialize components
            con = get_connection()
            exporter = ParquetExporter(con, ExportConfig())
            uploader = InternetArchiveUploader(UploadConfig())
            orchestrator = ExportOrchestrator(con, exporter, uploader)

            cleanup_files = not no_cleanup

            if backfill:
                # Backfill mode
                if not start_date or not end_date:
                    typer.secho(
                        "❌ Backfill requires --start-date and --end-date",
                        fg=typer.colors.RED,
                    )
                    raise typer.Exit(code=1)

                typer.echo(f"Starting backfill from {start_date} to {end_date}...")

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True,
                ) as progress:
                    progress.add_task(description="Backfilling exports...", total=None)
                    result = await orchestrator.backfill_historical(
                        start_date,
                        end_date,
                        cleanup_files,
                    )

                # Display results
                typer.echo("\n✅ Backfill complete!")
                typer.echo(f"  Date range: {result['start_date']} to {result['end_date']}")
                typer.echo(f"  Days processed: {result['successful_days']}/{result['total_days']}")
                typer.echo(f"  Successful exports: {result['successful_exports']}")
                typer.echo(f"  Failed exports: {result['failed_exports']}")

            elif tribunal:
                # Single tribunal export
                typer.echo(f"Exporting {tribunal} for {date or 'yesterday'}...")

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True,
                ) as progress:
                    progress.add_task(description=f"Exporting {tribunal}...", total=None)
                    file_path, row_count = await exporter.export_day_tribunal(date, tribunal)

                    file_size_mb = file_path.stat().st_size / (1024 * 1024)

                    progress.add_task(description="Uploading to Internet Archive...", total=None)
                    ia_url = await uploader.upload_parquet(
                        file_path,
                        tribunal,
                        date,
                        file_size_mb,
                        row_count,
                    )

                typer.echo("\n✅ Export complete!")
                typer.echo(f"  Tribunal: {tribunal}")
                typer.echo(f"  Date: {date}")
                typer.echo(f"  Rows: {row_count:,}")
                typer.echo(f"  Size: {file_size_mb:.2f} MB")
                typer.echo(f"  IA URL: {ia_url}")

            else:
                # Daily export for all tribunals
                export_date = date or "yesterday"
                typer.echo(f"Starting daily export for {export_date}...")

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True,
                ) as progress:
                    progress.add_task(description="Exporting all tribunals...", total=None)
                    result = await orchestrator.run_daily_export(date, cleanup_files)

                # Display results
                success_rate = (
                    100 * result["successful"] / result["total_tribunals"]
                    if result["total_tribunals"] > 0
                    else 0
                )

                typer.echo("\n✅ Daily export complete!")
                typer.echo(f"  Date: {result['date']}")
                typer.echo(
                    f"  Successful: {result['successful']}/{result['total_tribunals']} ({success_rate:.1f}%)",
                )
                typer.echo(f"  Failed: {result['failed']}")
                typer.echo(f"  Skipped (already exported): {result['skipped']}")
                typer.echo(f"  Total rows: {result['total_rows']:,}")
                typer.echo(f"  Total size: {result['total_size_mb']:.1f} MB")
                typer.echo(f"  Duration: {result['duration_seconds']:.1f}s")

                if result["failures"]:
                    typer.echo("\n❌ Failed tribunals:")
                    for failure in result["failures"]:
                        typer.echo(f"  - {failure['tribunal']}: {failure['error']}")

        except Exception as e:
            _handle_error(e, "Export failed")

    asyncio.run(_run())


@app.command()
def export_status(
    tribunal: str | None = typer.Option(None, help="Filter by tribunal"),
    days: int = typer.Option(7, help="Show last N days"),
    failed_only: bool = typer.Option(False, help="Show only failed exports"),
) -> None:
    """Show Parquet export status and statistics."""
    logger.info("export_status_command", tribunal=tribunal, days=days)

    try:
        con = get_connection()

        # Build query
        conditions = []
        params = []

        if tribunal:
            conditions.append("tribunal = ?")
            params.append(tribunal)

        if failed_only:
            conditions.append("status = 'failed'")

        # Get date range
        from datetime import date, timedelta

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        conditions.append("partition_date >= ? AND partition_date <= ?")
        params.extend([start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Query exports
        query = f"""
            SELECT
                partition_date,
                tribunal,
                status,
                row_count,
                file_size_mb,
                ia_url,
                error_message
            FROM parquet_exports
            WHERE {where_clause}
            ORDER BY partition_date DESC, tribunal
        """

        result = con.con.execute(query, params).fetchall()

        if not result:
            typer.echo("No exports found matching criteria.")
            return

        # Display results
        typer.echo(f"\n📊 Export Status (last {days} days):\n")

        current_date = None
        for row in result:
            pdate, trib, status, rows, size, url, error = row

            if pdate != current_date:
                if current_date:
                    typer.echo()  # Blank line between dates
                typer.echo(f"📅 {pdate}:")
                current_date = pdate

            status_icon = "✓" if status == "completed" else "✗" if status == "failed" else "⏳"
            status_color = (
                typer.colors.GREEN
                if status == "completed"
                else typer.colors.RED
                if status == "failed"
                else typer.colors.YELLOW
            )

            typer.echo(f"  {status_icon} ", nl=False)
            typer.secho(f"{trib:6}", fg=status_color, nl=False)
            typer.echo(f" | {rows:>7,} rows | {size:>6.1f} MB | {status:>10}", nl=False)

            if error:
                typer.echo(f" | Error: {error[:50]}")
            else:
                typer.echo()

        # Summary statistics
        typer.echo("\n📈 Summary:")

        stats_query = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(row_count) as total_rows,
                SUM(file_size_mb) as total_size
            FROM parquet_exports
            WHERE partition_date >= ? AND partition_date <= ?
        """

        if tribunal:
            stats_query += " AND tribunal = ?"
            stats_params = [
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                tribunal,
            ]
        else:
            stats_params = [start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")]

        stats = con.con.execute(stats_query, stats_params).fetchone()

        total, completed, failed, total_rows, total_size = stats
        success_rate = 100 * completed / total if total > 0 else 0

        typer.echo(f"  Total exports: {total}")
        typer.echo(f"  Completed: {completed} ({success_rate:.1f}%)")
        typer.echo(f"  Failed: {failed}")
        typer.echo(f"  Total rows: {total_rows:,}")
        typer.echo(f"  Total size: {total_size:.1f} MB")

    except Exception as e:
        _handle_error(e, "Failed to get export status")


# Ground truth management commands
groundtruth_app = typer.Typer(help="Ground truth management for RAG")
app.add_typer(groundtruth_app, name="groundtruth")


@groundtruth_app.command("status")
def groundtruth_status() -> None:
    """Check ground truth vector store status."""
    try:
        from causaganha.analysis.vector_store import VectorStore

        store = VectorStore()
        tables = store.list_tables()

        typer.echo("Vector Store Status:")
        typer.echo(f"  Location: {store.db_path}")
        typer.echo(f"  Tables: {len(tables)}")

        if "ground_truth" in tables:
            info = store.get_table_info("ground_truth")
            typer.echo("\n✅ Ground truth table exists:")
            typer.echo(f"  Records: {info['num_records']}")
        else:
            typer.echo("\n❌ Ground truth table not found.")
            typer.echo("Run 'causaganha groundtruth init' to create it.")

    except Exception as e:
        _handle_error(e, "Failed to check ground truth status")


@groundtruth_app.command("init")
def groundtruth_init(
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing table"),
) -> None:
    """Initialize ground truth vector store."""
    try:
        from causaganha.analysis.ground_truth import GroundTruthManager

        manager = GroundTruthManager()
        manager.init_store(overwrite=overwrite)
        typer.echo("✅ Ground truth vector store initialized.")
    except Exception as e:
        _handle_error(e, "Failed to initialize ground truth")


@groundtruth_app.command("sync")
def groundtruth_sync(
    min_confidence: float = typer.Option(0.90, help="Minimum confidence threshold"),
    limit: int = typer.Option(100, help="Maximum records to sync"),
) -> None:
    """Sync high-confidence analyses from DuckDB to vector store."""
    logger.info("groundtruth_sync_command", min_confidence=min_confidence, limit=limit)

    async def _run() -> None:
        try:
            from causaganha.analysis.ground_truth import GroundTruthManager

            con = get_connection()
            manager = GroundTruthManager()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Syncing Ground Truth...", total=None)
                result = await manager.sync_from_db(
                    con,
                    min_confidence=min_confidence,
                    limit=limit,
                )

            if result["status"] == "success":
                typer.echo(f"✅ Sync complete! Added {result['synced']} new examples.")
            elif result["status"] == "no_data":
                typer.echo("ℹ️ No high-confidence records found in database.")
            elif result["status"] == "already_synced":
                typer.echo("ℹ️ All available records are already in the vector store.")

        except Exception as e:
            _handle_error(e, "Sync failed")

    asyncio.run(_run())


@groundtruth_app.command("search")
def groundtruth_search(
    query: str = typer.Argument(..., help="Text to search for"),
    k: int = typer.Option(5, help="Number of results"),
) -> None:
    """Search for similar examples in ground truth."""
    logger.info("groundtruth_search_command", k=k)

    async def _run() -> None:
        try:
            from causaganha.analysis.ground_truth import GroundTruthManager

            manager = GroundTruthManager()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Searching...", total=None)
                results = await manager.search(query, k=k)

            if not results:
                typer.echo("No matching examples found.")
                return

            typer.echo(f"\n🔍 Top {len(results)} matches for: '{query}'\n")

            for i, res in enumerate(results, 1):
                outcome = res.get("outcome", "UNKNOWN")
                score = 1 - res.get("_distance", 1.0)  # Convert L2 distance to approx similarity
                int_id = res.get("intimation_id", "N/A")
                text = res.get("text", "")[:120].replace("\n", " ")

                color = (
                    typer.colors.GREEN
                    if outcome == "WIN"
                    else typer.colors.RED
                    if outcome == "LOSS"
                    else typer.colors.YELLOW
                    if outcome == "PARTIAL"
                    else typer.colors.WHITE
                )

                typer.echo(f"{i}. ", nl=False)
                typer.secho(f"[{outcome}]", fg=color, bold=True, nl=False)
                typer.echo(f" ID: {int_id} | Similarity: {score:.3f}")
                typer.echo(f"    {text}...")

        except Exception as e:
            _handle_error(e, "Search failed")

    asyncio.run(_run())


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


# Parquet analysis commands
parquet_app = typer.Typer(help="Parquet-based analysis workflows")
app.add_typer(parquet_app, name="parquet")


@parquet_app.command("analyze")
def analyze_parquet_file(
    file: str = typer.Argument(..., help="Path to parquet file"),
    strategy: str = typer.Option(
        "hybrid",
        help="Analysis strategy: llm, rag, hybrid, auto",
    ),
    output_mode: str = typer.Option(
        "parquet",
        help="Output mode: parquet, duckdb, both, none",
    ),
    confidence_threshold: float = typer.Option(
        0.70,
        help="Confidence threshold for hybrid strategy",
    ),
    filter_unanalyzed: bool = typer.Option(
        True,
        help="Only analyze rows without analysis",
    ),
) -> None:
    """Analyze decisions from a local parquet file."""
    logger.info("analyze_parquet_command", file=file, strategy=strategy)

    async def _run() -> None:
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task_desc = f"Analyzing from parquet ({strategy} strategy)..."
                progress.add_task(description=task_desc, total=None)

                result = await analyze_from_parquet(
                    parquet_path=file,
                    strategy=strategy,
                    output_mode=output_mode,
                    confidence_threshold=confidence_threshold,
                    filter_unanalyzed=filter_unanalyzed,
                )

            # Display results
            typer.echo("\n✅ Parquet analysis complete!")
            typer.echo(f"  Strategy: {strategy}")
            typer.echo(f"  Analyzed: {result['analyzed']}")
            typer.echo(f"  Failed: {result['failed']}")
            typer.echo(f"  Skipped: {result.get('skipped', 0)}")

            if strategy in ["hybrid", "auto"]:
                total = result["analyzed"]
                if total > 0:
                    typer.echo(
                        f"  RAG used: {result['rag_used']} ({result['rag_used']/total*100:.1f}%)",
                    )
                    typer.echo(
                        f"  LLM used: {result['llm_used']} ({result['llm_used']/total*100:.1f}%)",
                    )

            if "total_cost" in result:
                typer.echo(f"  Total cost: ${result['total_cost']:.6f}")

            if "output_file" in result:
                typer.echo(f"  Output file: {result['output_file']}")

        except Exception as e:
            _handle_error(e, "Parquet analysis failed")

    asyncio.run(_run())


@parquet_app.command("analyze-ia")
def analyze_from_ia(
    tribunal: str = typer.Argument(..., help="Tribunal code (e.g., TJRO)"),
    date: str = typer.Argument(..., help="Date in YYYY-MM-DD format"),
    strategy: str = typer.Option(
        "hybrid",
        help="Analysis strategy: llm, rag, hybrid, auto",
    ),
    output_mode: str = typer.Option(
        "parquet",
        help="Output mode: parquet, duckdb, both, none",
    ),
    confidence_threshold: float = typer.Option(
        0.70,
        help="Confidence threshold for hybrid strategy",
    ),
) -> None:
    """Analyze decisions from Internet Archive parquet file."""
    logger.info("analyze_ia_command", tribunal=tribunal, date=date, strategy=strategy)

    async def _run() -> None:
        try:
            from causaganha.pipeline.analyze_parquet import analyze_from_ia as analyze_ia_func

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Downloading from Internet Archive...", total=None)
                progress.add_task(description=f"Analyzing ({strategy} strategy)...", total=None)

                result = await analyze_ia_func(
                    tribunal=tribunal,
                    date=date,
                    strategy=strategy,
                    output_mode=output_mode,
                    confidence_threshold=confidence_threshold,
                )

            # Display results
            typer.echo("\n✅ Internet Archive analysis complete!")
            typer.echo(f"  Tribunal: {tribunal}")
            typer.echo(f"  Date: {date}")
            typer.echo(f"  Strategy: {strategy}")
            typer.echo(f"  Analyzed: {result['analyzed']}")
            typer.echo(f"  Failed: {result['failed']}")
            typer.echo(f"  Skipped: {result.get('skipped', 0)}")

            if strategy in ["hybrid", "auto"]:
                total = result["analyzed"]
                if total > 0:
                    typer.echo(
                        f"  RAG used: {result['rag_used']} ({result['rag_used']/total*100:.1f}%)",
                    )
                    typer.echo(
                        f"  LLM used: {result['llm_used']} ({result['llm_used']/total*100:.1f}%)",
                    )

            if "total_cost" in result:
                typer.echo(f"  Total cost: ${result['total_cost']:.6f}")

            if "output_file" in result:
                typer.echo(f"  Output file: {result['output_file']}")

        except Exception as e:
            _handle_error(e, "Internet Archive analysis failed")

    asyncio.run(_run())


@parquet_app.command("download")
def download_parquet(
    tribunal: str = typer.Argument(..., help="Tribunal code (e.g., TJRO)"),
    date: str = typer.Argument(..., help="Date in YYYY-MM-DD format"),
    force: bool = typer.Option(False, help="Force re-download (ignore cache)"),
    cache_dir: str = typer.Option("./ia_cache", help="Cache directory"),
) -> None:
    """Download parquet file from Internet Archive."""
    logger.info("download_parquet_command", tribunal=tribunal, date=date)

    async def _run() -> None:
        try:
            from pathlib import Path

            from causaganha.pipeline.ia_download import DownloadConfig, IAParquetDownloader

            config = DownloadConfig(cache_dir=Path(cache_dir))
            downloader = IAParquetDownloader(config=config)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Downloading from Internet Archive...", total=None)

                file_path = await downloader.download(
                    tribunal=tribunal,
                    date=date,
                    force_refresh=force,
                )

            # Display results
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            typer.echo("\n✅ Download complete!")
            typer.echo(f"  Tribunal: {tribunal}")
            typer.echo(f"  Date: {date}")
            typer.echo(f"  File: {file_path}")
            typer.echo(f"  Size: {file_size_mb:.2f} MB")

            # Get IA URL
            ia_url = await downloader.get_item_url(tribunal, date)
            typer.echo(f"  Source: {ia_url}")

        except Exception as e:
            _handle_error(e, "Download failed")

    asyncio.run(_run())


@parquet_app.command("check")
def check_ia_exists(
    tribunal: str = typer.Argument(..., help="Tribunal code (e.g., TJRO)"),
    date: str = typer.Argument(..., help="Date in YYYY-MM-DD format"),
) -> None:
    """Check if parquet file exists on Internet Archive."""
    logger.info("check_ia_command", tribunal=tribunal, date=date)

    async def _run() -> None:
        try:
            from causaganha.pipeline.ia_download import IAParquetDownloader

            downloader = IAParquetDownloader()
            exists = await downloader.check_exists(tribunal, date)

            ia_url = await downloader.get_item_url(tribunal, date)

            if exists:
                typer.echo("✅ Parquet file exists on Internet Archive")
                typer.echo(f"  Tribunal: {tribunal}")
                typer.echo(f"  Date: {date}")
                typer.echo(f"  URL: {ia_url}")
            else:
                typer.echo("❌ Parquet file not found on Internet Archive")
                typer.echo(f"  Tribunal: {tribunal}")
                typer.echo(f"  Date: {date}")
                typer.echo(f"  Expected URL: {ia_url}")

        except Exception as e:
            _handle_error(e, "Check failed")

    asyncio.run(_run())


@parquet_app.command("clear-cache")
def clear_parquet_cache(
    older_than_days: int = typer.Option(
        None,
        help="Only delete files older than N days (None = all)",
    ),
    cache_dir: str = typer.Option("./ia_cache", help="Cache directory"),
) -> None:
    """Clear downloaded parquet cache."""
    logger.info("clear_cache_command", older_than_days=older_than_days)

    try:
        from pathlib import Path

        from causaganha.pipeline.ia_download import DownloadConfig, IAParquetDownloader

        config = DownloadConfig(cache_dir=Path(cache_dir))
        downloader = IAParquetDownloader(config=config)

        deleted = downloader.clear_cache(older_than_days=older_than_days)

        typer.echo(f"✅ Cleared {deleted} cached files")
        if older_than_days:
            typer.echo(f"  (files older than {older_than_days} days)")

    except Exception as e:
        _handle_error(e, "Cache clear failed")


# Catalog management commands
catalog_app = typer.Typer(help="DuckDB metadata catalog management")
app.add_typer(catalog_app, name="catalog")


@catalog_app.command("create")
def create_catalog(
    output: str = typer.Option(
        "causaganha-catalog.duckdb",
        help="Output path for catalog database",
    ),
    month: str | None = typer.Option(
        None,
        help="Month pattern (e.g., 2026-01) for versioned catalog",
    ),
    include_views: str | None = typer.Option(
        None,
        help="Comma-separated list of analytical views to include",
    ),
) -> None:
    """Create a metadata catalog that references remote Parquet files."""
    logger.info("create_catalog_command", output=output, month=month)

    try:
        from causaganha.catalog.creator import CatalogCreator

        typer.echo(f"Creating metadata catalog: {output}")

        creator = CatalogCreator(output)
        creator.create()

        # Add standard views
        date_pattern = f"{month}-*" if month else None
        creator.add_standard_views(date_pattern=date_pattern)

        # Validate catalog
        validation_results = creator.validate()

        # Display results
        info = creator.get_catalog_info()

        typer.echo("\n✅ Catalog created successfully!")
        typer.echo(f"  Path: {info['path']}")
        typer.echo(f"  Size: {info['size_kb']} KB")
        typer.echo(f"  Views: {info['view_count']}")

        if month:
            typer.echo(f"  Month: {month}")

        typer.echo("\n📊 Views created:")
        for view in info["views"]:
            typer.echo(f"  - {view['name']}")

        # Display validation results
        typer.echo("\n✓ Validation:")
        for result in validation_results:
            status_icon = (
                "✓"
                if result["status"] == "passed"
                else "⚠"
                if result["status"] == "warning"
                else "✗"
            )
            typer.echo(f"  {status_icon} {result['check']}: {result['message']}")

    except Exception as e:
        _handle_error(e, "Catalog creation failed")


@catalog_app.command("list")
def list_catalog_views(
    catalog: str = typer.Argument(..., help="Path to catalog database"),
) -> None:
    """List all views in a catalog."""
    logger.info("list_catalog_command", catalog=catalog)

    try:
        from causaganha.catalog.creator import CatalogCreator

        if not os.path.exists(catalog):
            typer.secho(f"❌ Catalog not found: {catalog}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        creator = CatalogCreator(catalog)
        views = creator.list_views()

        typer.echo(f"\n📋 Views in {catalog}:\n")

        for i, view in enumerate(views, 1):
            typer.echo(f"{i}. {view['name']}")
            # Show first 80 chars of SQL
            sql_preview = view["sql"][:80] + "..." if len(view["sql"]) > 80 else view["sql"]
            typer.echo(f"   {sql_preview}\n")

        typer.echo(f"Total: {len(views)} views")

    except Exception as e:
        _handle_error(e, "Failed to list views")


@catalog_app.command("info")
def catalog_info(
    catalog: str = typer.Argument(..., help="Path to catalog database"),
) -> None:
    """Show detailed catalog information."""
    logger.info("catalog_info_command", catalog=catalog)

    try:
        from causaganha.catalog.creator import CatalogCreator

        if not os.path.exists(catalog):
            typer.secho(f"❌ Catalog not found: {catalog}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        creator = CatalogCreator(catalog)
        info = creator.get_catalog_info()

        typer.echo("\n📊 Catalog Information:\n")
        typer.echo(f"  Path: {info['path']}")
        typer.echo(f"  Size: {info['size_bytes']:,} bytes ({info['size_kb']} KB)")
        typer.echo(f"  Views: {info['view_count']}")

        typer.echo("\n📋 Views:")
        for view in info["views"]:
            typer.echo(f"  - {view['name']}")

    except Exception as e:
        _handle_error(e, "Failed to get catalog info")


@catalog_app.command("validate")
def validate_catalog(
    catalog: str = typer.Argument(..., help="Path to catalog database"),
) -> None:
    """Validate a catalog database."""
    logger.info("validate_catalog_command", catalog=catalog)

    try:
        from causaganha.catalog.creator import CatalogCreator

        creator = CatalogCreator(catalog)
        validation_results = creator.validate()

        typer.echo("\n🔍 Catalog Validation:\n")

        all_passed = True
        for result in validation_results:
            status = result["status"]
            check = result["check"]
            message = result["message"]

            if status == "passed":
                typer.secho(f"  ✓ {check}: {message}", fg=typer.colors.GREEN)
            elif status == "warning":
                typer.secho(f"  ⚠ {check}: {message}", fg=typer.colors.YELLOW)
                all_passed = False
            else:
                typer.secho(f"  ✗ {check}: {message}", fg=typer.colors.RED)
                all_passed = False

        if all_passed:
            typer.echo("\n✅ Catalog is valid!")
        else:
            typer.echo("\n⚠ Catalog has warnings or errors")

    except Exception as e:
        _handle_error(e, "Validation failed")


if __name__ == "__main__":
    app()
