#!/usr/bin/env python3
"""Download real legal data from Internet Archive for benchmarking.

Downloads parquet files from CausaGanha's Internet Archive collection
and loads them into DuckDB for quality benchmarking with REAL data.

Usage:
    python scripts/download_real_data_from_ia.py
    python scripts/download_real_data_from_ia.py --tribunal TJRO --limit 5
"""

import asyncio
from pathlib import Path

import duckdb
import internetarchive as ia
import structlog
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from causaganha.config import settings


logger = structlog.get_logger()
console = Console()
app = typer.Typer()


class IADataDownloader:
    """Download and load CausaGanha data from Internet Archive."""

    def __init__(self, cache_dir: Path | None = None):
        """Initialize downloader.

        Args:
            cache_dir: Directory to cache downloaded files (default: data/ia_cache).
        """
        self.cache_dir = cache_dir or (settings.DATA_DIR / "ia_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info("ia_downloader_initialized", cache_dir=str(self.cache_dir))

    def search_causaganha_items(
        self,
        tribunal: str | None = None,
        limit: int = 10,
    ) -> list[str]:
        """Search for CausaGanha items on Internet Archive.

        Args:
            tribunal: Filter by tribunal (e.g., "TJRO"). None = all tribunals.
            limit: Maximum number of items to return.

        Returns:
            List of item identifiers.
        """
        console.print("\n[cyan]Searching Internet Archive for CausaGanha data...[/cyan]")

        # Build search query
        if tribunal:
            query = f"collection:causaganha AND subject:{tribunal}"
        else:
            query = "collection:causaganha"

        # Search Internet Archive
        search = ia.search_items(query, sorts=["publicdate desc"])

        item_ids = []
        for i, result in enumerate(search):
            if i >= limit:
                break
            item_ids.append(result["identifier"])

        console.print(f"  ✓ Found {len(item_ids)} items")
        return item_ids

    def download_item_parquet(self, item_id: str) -> Path | None:
        """Download parquet file from an Internet Archive item.

        Args:
            item_id: Internet Archive item identifier.

        Returns:
            Path to downloaded parquet file, or None if no parquet found.
        """
        # Check if already cached
        cached_file = self.cache_dir / f"{item_id}.parquet"
        if cached_file.exists():
            logger.info("using_cached_file", item_id=item_id, file=str(cached_file))
            return cached_file

        # Download from IA
        try:
            item = ia.get_item(item_id)

            # Find parquet file
            parquet_file = None
            for file in item.files:
                if file["name"].endswith(".parquet"):
                    parquet_file = file
                    break

            if not parquet_file:
                logger.warning("no_parquet_file_found", item_id=item_id)
                return None

            # Download file
            logger.info(
                "downloading_from_ia",
                item_id=item_id,
                filename=parquet_file["name"],
                size_mb=float(parquet_file.get("size", 0)) / 1024 / 1024,
            )

            item.download(
                files=[parquet_file["name"]],
                destdir=str(self.cache_dir),
                verbose=False,
                silent=True,
            )

            # Rename to standard format
            downloaded_path = self.cache_dir / parquet_file["name"]
            if downloaded_path.exists():
                downloaded_path.rename(cached_file)
                logger.info("download_complete", item_id=item_id, file=str(cached_file))
                return cached_file

            logger.error("download_failed", item_id=item_id)
            return None

        except Exception as e:
            logger.exception("download_error", item_id=item_id, error=str(e))
            return None

    def load_parquet_to_duckdb(
        self,
        parquet_files: list[Path],
        db_path: Path,
    ) -> dict[str, int]:
        """Load parquet files into DuckDB database.

        Args:
            parquet_files: List of parquet file paths.
            db_path: Path to DuckDB database.

        Returns:
            Dict with counts of loaded records.
        """
        console.print(f"\n[cyan]Loading {len(parquet_files)} parquet files into DuckDB...[/cyan]")

        conn = duckdb.connect(str(db_path))

        # Ensure schema exists
        schema_file = Path(__file__).parent.parent / "src/causaganha/v2/storage/schema.sql"
        if schema_file.exists():
            with schema_file.open() as f:
                schema_sql = f.read()
            conn.execute(schema_sql)
            logger.info("schema_created")

        total_intimations = 0
        total_analyses = 0

        for parquet_file in parquet_files:
            try:
                logger.info("loading_parquet", file=str(parquet_file))

                # Read parquet structure to determine what tables to populate
                # Check if parquet has the columns we need
                result = conn.execute(
                    f"SELECT COUNT(*) FROM read_parquet('{parquet_file}')"
                ).fetchone()

                if result:
                    row_count = result[0]
                    console.print(f"  • {parquet_file.name}: {row_count} rows")

                    # Load into intimations table
                    # Note: Adjust column mapping based on your actual parquet schema
                    conn.execute(
                        f"""
                        INSERT OR IGNORE INTO intimations
                        SELECT * FROM read_parquet('{parquet_file}')
                        WHERE texto IS NOT NULL
                        """
                    )

                    total_intimations += row_count

            except Exception as e:
                logger.exception("failed_to_load_parquet", file=str(parquet_file), error=str(e))
                console.print(f"  ✗ Failed to load {parquet_file.name}: {e}", style="red")

        # Get final counts
        intimations_count = conn.execute("SELECT COUNT(*) FROM intimations").fetchone()[0]
        analyses_count = conn.execute("SELECT COUNT(*) FROM decision_analysis").fetchone()[0]

        conn.close()

        console.print(f"\n  ✓ Loaded {intimations_count} intimations, {analyses_count} analyses")

        return {
            "intimations": intimations_count,
            "analyses": analyses_count,
        }


@app.command()
def main(
    tribunal: str | None = typer.Option(
        None,
        "--tribunal",
        "-t",
        help="Filter by tribunal (e.g., TJRO)",
    ),
    limit: int = typer.Option(
        5,
        "--limit",
        "-n",
        help="Maximum number of items to download",
    ),
    db_path: str = typer.Option(
        str(settings.DATA_DIR / "causaganha_real.duckdb"),
        "--db",
        help="Path to DuckDB database",
    ),
    cache_dir: str | None = typer.Option(
        None,
        "--cache-dir",
        help="Directory to cache downloaded files",
    ),
) -> None:
    """Download real legal data from Internet Archive for benchmarking.

    This downloads actual parquet files from CausaGanha's Internet Archive
    collection and loads them into a DuckDB database for quality benchmarking.
    """
    console.print("[bold]Download Real Data from Internet Archive[/bold]")
    console.print(f"Tribunal filter: {tribunal or 'All'}")
    console.print(f"Limit: {limit} items")
    console.print(f"Database: {db_path}\n")

    try:
        # Initialize downloader
        cache_path = Path(cache_dir) if cache_dir else None
        downloader = IADataDownloader(cache_dir=cache_path)

        # Search for items
        item_ids = downloader.search_causaganha_items(tribunal=tribunal, limit=limit)

        if not item_ids:
            console.print("[red]No items found on Internet Archive.[/red]")
            console.print("\n[yellow]Make sure you have uploaded data to Internet Archive first.[/yellow]")
            raise typer.Exit(1)

        # Download parquet files
        parquet_files = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Downloading from Internet Archive...", total=len(item_ids))

            for item_id in item_ids:
                progress.update(task, description=f"Downloading {item_id}...")
                parquet_file = downloader.download_item_parquet(item_id)

                if parquet_file:
                    parquet_files.append(parquet_file)

                progress.advance(task)

        if not parquet_files:
            console.print("\n[red]No parquet files downloaded.[/red]")
            raise typer.Exit(1)

        console.print(f"\n[green]✓ Downloaded {len(parquet_files)} parquet files[/green]")

        # Load into DuckDB
        db_path_obj = Path(db_path)
        counts = downloader.load_parquet_to_duckdb(parquet_files, db_path_obj)

        # Print summary
        console.print("\n[bold green]✓ Real data loaded successfully![/bold green]")
        console.print(f"\nDatabase: {db_path}")
        console.print(f"Intimations: {counts['intimations']}")
        console.print(f"Analyses: {counts['analyses']}")

        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        console.print("Run quality benchmarks with real data:")
        console.print(f"  uv run python scripts/benchmark_embedding_quality.py --db {db_path}")
        console.print(f"  uv run python scripts/benchmark_winner_loser_accuracy.py --db {db_path}")

    except KeyboardInterrupt:
        console.print("\n[yellow]Download interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Download failed: {e}[/red]")
        logger.exception("download_failed", error=str(e))
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
