"""Catalog management commands."""

import asyncio
import csv
import json
import re
import sys
from pathlib import Path

import duckdb
import httpx
import structlog
import typer

from causaganha.cli.utils import handle_error


logger = structlog.get_logger()

catalog_app = typer.Typer(help="DuckDB metadata catalog management")


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
    _include_views: str | None = typer.Option(
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
        handle_error(e, "Catalog creation failed")


@catalog_app.command("list")
def list_catalog_views(
    catalog: str = typer.Argument(..., help="Path to catalog database"),
) -> None:
    """List all views in a catalog."""
    logger.info("list_catalog_command", catalog=catalog)

    try:
        from causaganha.catalog.creator import CatalogCreator

        if not Path(catalog).exists():
            typer.secho(f"❌ Catalog not found: {catalog}", fg=typer.colors.RED)
            raise typer.Exit(code=1)  # noqa: TRY301

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
        handle_error(e, "Failed to list views")


@catalog_app.command("info")
def catalog_info(
    catalog: str = typer.Argument(..., help="Path to catalog database"),
) -> None:
    """Show detailed catalog information."""
    logger.info("catalog_info_command", catalog=catalog)

    try:
        from causaganha.catalog.creator import CatalogCreator

        if not Path(catalog).exists():
            typer.secho(f"❌ Catalog not found: {catalog}", fg=typer.colors.RED)
            raise typer.Exit(code=1)  # noqa: TRY301

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
        handle_error(e, "Failed to get catalog info")


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
        handle_error(e, "Validation failed")


@catalog_app.command("download")
def download_catalog(
    output: str = typer.Option(
        "./causaganha-catalog",
        help="Output directory for downloaded catalog files",
    ),
    force: bool = typer.Option(False, help="Force re-download even if files exist"),
) -> None:
    """Download master catalog from Internet Archive."""
    logger.info("download_catalog_command", output=output)

    async def _run() -> None:
        try:
            ia_catalog_item = "causaganha-catalog"
            base_url = f"https://archive.org/download/{ia_catalog_item}"

            files_to_download = [
                "manifest.parquet",
                "backfill-needed.parquet",
                "catalog.sql",
                "catalog.duckdb",
            ]

            output_dir = Path(output)
            output_dir.mkdir(parents=True, exist_ok=True)

            typer.echo("Downloading catalog from Internet Archive...")
            typer.echo(f"  Item: {ia_catalog_item}")
            typer.echo(f"  Output: {output_dir}\n")

            async with httpx.AsyncClient(timeout=60.0) as client:
                for filename in files_to_download:
                    output_path = output_dir / filename

                    if output_path.exists() and not force:
                        typer.echo(f"  ⏭ {filename} (exists, use --force to re-download)")
                        continue

                    url = f"{base_url}/{filename}"
                    typer.echo(f"  ⬇ {filename}...", nl=False)

                    try:
                        response = await client.get(url)
                        if response.status_code == 200:
                            content = response.content

                            # Basic validation: check file is not empty
                            if len(content) < 100:
                                typer.echo(" (warning: file too small, may be corrupted)")
                                continue

                            # Validate parquet files have correct magic bytes
                            if filename.endswith(".parquet") and not (
                                content[:4] == b"PAR1" or content[-4:] == b"PAR1"
                            ):
                                typer.echo(" (warning: invalid parquet file)")
                                continue

                            # Validate DuckDB files
                            if filename.endswith(".duckdb") and len(content) < 1024:
                                typer.echo(" (warning: duckdb file too small)")
                                continue

                            output_path.write_bytes(content)
                            size_kb = len(content) / 1024
                            typer.echo(f" ({size_kb:.1f} KB)")
                        elif response.status_code == 404:
                            typer.echo(" (not found - catalog may not exist yet)")
                        else:
                            typer.echo(f" (HTTP {response.status_code})")
                    except httpx.TimeoutException:
                        typer.echo(" (timeout - try again later)")
                    except httpx.ConnectError:
                        typer.echo(" (connection error - check internet)")
                    except Exception as e:
                        typer.echo(f" (error: {type(e).__name__})")

            # Verify at least some files were downloaded
            downloaded = [f for f in files_to_download if (output_dir / f).exists()]
            if not downloaded:
                typer.secho("\n⚠ No files were downloaded.", fg=typer.colors.YELLOW)
                typer.echo("The catalog may not exist yet on Internet Archive.")
            else:
                typer.echo(f"\n✅ Downloaded {len(downloaded)}/{len(files_to_download)} files")
                typer.echo(f"  Location: {output_dir}")

        except Exception as e:
            handle_error(e, "Download failed")

    asyncio.run(_run())


def _validate_tribunal_code(tribunal: str | None) -> str | None:
    """Validate tribunal code to prevent SQL injection and invalid values."""
    if tribunal is None:
        return None

    # Tribunal codes are uppercase alphanumeric, max 10 chars
    if not re.match(r"^[A-Z0-9-]{2,10}$", tribunal.upper()):
        return None

    return tribunal.upper()


def _validate_parquet_schema(
    con: duckdb.DuckDBPyConnection,
    path: str,
    required_cols: list[str],
) -> bool:
    """Check if parquet file has required columns."""
    try:
        schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}') LIMIT 0").fetchall()  # noqa: S608
        columns = {row[0].lower() for row in schema}
        return all(col.lower() in columns for col in required_cols)
    except Exception:
        return False


@catalog_app.command("backfill-status")
def backfill_status(
    catalog_dir: str = typer.Option(
        "./causaganha-catalog",
        help="Directory containing catalog files",
    ),
    tribunal: str | None = typer.Option(None, help="Filter by tribunal"),
    limit: int = typer.Option(20, help="Maximum items to show"),
) -> None:
    """Show what data needs to be backfilled from DJEN."""
    logger.info("backfill_status_command", catalog_dir=catalog_dir)

    try:
        backfill_path = Path(catalog_dir) / "backfill-needed.parquet"

        if not backfill_path.exists():
            typer.secho(
                f"❌ Backfill file not found: {backfill_path}",
                fg=typer.colors.RED,
            )
            typer.echo("Run 'causaganha catalog download' first.")
            raise typer.Exit(code=1)

        # Validate tribunal parameter to prevent SQL injection
        validated_tribunal = _validate_tribunal_code(tribunal)
        if tribunal and not validated_tribunal:
            typer.secho(
                f"❌ Invalid tribunal code: {tribunal}",
                fg=typer.colors.RED,
            )
            typer.echo("Tribunal codes should be 2-10 uppercase alphanumeric characters.")
            raise typer.Exit(code=1)

        con = duckdb.connect(":memory:")

        # Validate parquet schema before querying
        required_cols = ["date", "tribunal"]
        if not _validate_parquet_schema(con, str(backfill_path), required_cols):
            typer.secho(
                f"❌ Malformed backfill file: missing required columns {required_cols}",
                fg=typer.colors.RED,
            )
            typer.echo("The file may be corrupted. Try re-downloading with --force.")
            con.close()
            raise typer.Exit(code=1)

        # Build query with parameterized filter (safe from injection)
        where_clause = f"WHERE tribunal = '{validated_tribunal}'" if validated_tribunal else ""

        # Get summary stats with error handling for empty/malformed data
        try:
            stats = con.execute(f"""
                SELECT
                    COUNT(*) as total_missing,
                    COUNT(DISTINCT tribunal) as tribunals,
                    COUNT(DISTINCT date) as days,
                    MIN(date) as earliest,
                    MAX(date) as latest
                FROM read_parquet('{backfill_path}')
                {where_clause}
            """).fetchone()  # noqa: S608
        except duckdb.Error as e:
            typer.secho(f"❌ Error reading backfill file: {e}", fg=typer.colors.RED)
            typer.echo("The file may be corrupted. Try re-downloading with --force.")
            con.close()
            raise typer.Exit(code=1) from e

        if stats is None or stats[0] == 0:
            typer.echo(
                "\n✅ No backfill needed!"
                if not validated_tribunal
                else f"\n✅ No backfill needed for {validated_tribunal}!",
            )
            con.close()
            return

        total, tribunals, days, earliest, latest = stats

        typer.echo("\n📊 Backfill Status:\n")
        typer.echo(f"  Total missing: {total:,} items")
        typer.echo(f"  Tribunals: {tribunals}")
        typer.echo(f"  Days: {days}")
        typer.echo(f"  Date range: {earliest} to {latest}")

        if validated_tribunal:
            typer.echo(f"  Filter: {validated_tribunal}")

        # Get breakdown by tribunal
        typer.echo("\n📋 Missing by Tribunal:")
        breakdown = con.execute(f"""
            SELECT
                tribunal,
                COUNT(*) as missing,
                MIN(date) as earliest,
                MAX(date) as latest
            FROM read_parquet('{backfill_path}')
            {where_clause}
            GROUP BY tribunal
            ORDER BY missing DESC
            LIMIT {limit}
        """).fetchall()  # noqa: S608

        for trib, missing, early, late in breakdown:
            # Handle None values gracefully
            trib_str = str(trib) if trib else "UNKNOWN"
            early_str = str(early) if early else "N/A"
            late_str = str(late) if late else "N/A"
            typer.echo(f"  {trib_str:6}: {missing:4} items ({early_str} to {late_str})")

        if len(breakdown) >= limit:
            typer.echo(f"  ... (showing top {limit}, use --limit to see more)")

        con.close()

    except duckdb.Error as e:
        handle_error(e, "Failed to read backfill status")


@catalog_app.command("query")
def query_catalog(
    query: str = typer.Argument(..., help="SQL query to execute"),
    catalog_dir: str = typer.Option(
        "./causaganha-catalog",
        help="Directory containing catalog files",
    ),
    output_format: str = typer.Option("table", help="Output format: table, csv, json"),
    limit: int = typer.Option(100, help="Maximum rows to return"),
) -> None:
    """Query the catalog using SQL."""
    logger.info("query_catalog_command", catalog_dir=catalog_dir)

    try:
        from pathlib import Path

        # Validate format parameter
        valid_formats = ["table", "csv", "json"]
        if output_format not in valid_formats:
            typer.secho(
                f"❌ Invalid format: {output_format}",
                fg=typer.colors.RED,
            )
            typer.echo(f"Valid formats: {', '.join(valid_formats)}")
            raise typer.Exit(code=1)  # noqa: TRY301

        catalog_path = Path(catalog_dir) / "catalog.duckdb"

        if not catalog_path.exists():
            typer.secho(
                f"❌ Catalog not found: {catalog_path}",
                fg=typer.colors.RED,
            )
            typer.echo("Run 'causaganha catalog download' first.")
            raise typer.Exit(code=1)  # noqa: TRY301

        # Try to open catalog file - may be corrupted
        try:
            con = duckdb.connect(str(catalog_path), read_only=True)
        except duckdb.Error as e:
            typer.secho(
                f"❌ Catalog file is corrupted: {e}",
                fg=typer.colors.RED,
            )
            typer.echo("Try re-downloading with: causaganha catalog download --force")
            raise typer.Exit(code=1) from e

        # Add LIMIT if not present
        if "LIMIT" not in query.upper():
            query = f"{query} LIMIT {limit}"

        # Execute query with error handling
        try:
            result = con.execute(query)
        except duckdb.ParserException as e:
            typer.secho(f"❌ SQL syntax error: {e}", fg=typer.colors.RED)
            con.close()
            raise typer.Exit(code=1) from e
        except duckdb.CatalogException as e:
            typer.secho(f"❌ Table or column not found: {e}", fg=typer.colors.RED)
            typer.echo("\nAvailable tables: manifest, backfill_needed")
            con.close()
            raise typer.Exit(code=1) from e
        except duckdb.Error as e:
            typer.secho(f"❌ Query error: {e}", fg=typer.colors.RED)
            con.close()
            raise typer.Exit(code=1) from e

        columns = [desc[0] for desc in result.description] if result.description else []
        rows = result.fetchall()

        # Handle empty results gracefully
        if not rows:
            typer.echo("\n(0 rows - no data matches your query)")
            con.close()
            return

        # Helper to safely convert values to strings
        def safe_str(v) -> str:
            if v is None:
                return "NULL"
            try:
                return str(v)
            except Exception:
                return "<error>"

        if output_format == "csv":
            writer = csv.writer(sys.stdout)
            writer.writerow(columns)
            # Safely convert all values
            for row in rows:
                writer.writerow([safe_str(v) for v in row])
        elif output_format == "json":
            # Safely build data with error handling for malformed values
            data = []
            for row in rows:
                row_dict = {}
                for col, val in zip(columns, row, strict=False):
                    try:
                        # Handle non-serializable types
                        if hasattr(val, "isoformat"):
                            row_dict[col] = val.isoformat()
                        else:
                            row_dict[col] = val
                    except Exception:
                        row_dict[col] = None
                data.append(row_dict)
            typer.echo(json.dumps(data, indent=2, default=str))
        else:
            # Table format with safe string conversion
            typer.echo("\n" + " | ".join(columns))
            typer.echo("-" * (len(" | ".join(columns)) + 10))
            for row in rows:
                typer.echo(" | ".join(safe_str(v) for v in row))

        typer.echo(f"\n({len(rows)} rows)")
        con.close()

    except duckdb.Error as e:
        handle_error(e, "Query failed")
    except Exception as e:
        # Catch any unexpected errors and provide helpful message
        typer.secho(f"⚠ Unexpected error: {e}", fg=typer.colors.YELLOW)
        typer.echo("The data may contain unexpected values. Try a simpler query.")
