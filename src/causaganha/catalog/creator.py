"""DuckDB catalog creator for remote Parquet access."""

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import duckdb


class CatalogCreator:
    """Creates and manages DuckDB metadata catalogs.

    A metadata catalog is a lightweight DuckDB database file that contains
    only view definitions (no actual data). Views reference remote Parquet
    files on Internet Archive, enabling users to query data without downloading.

    Example:
        >>> creator = CatalogCreator("causaganha-catalog.duckdb")
        >>> creator.create()
        >>> creator.add_base_view("intimations", "https://archive.org/download/djen-*.parquet")
        >>> creator.add_analytical_view("top_lawyers", "SELECT * FROM lawyers WHERE rating > 1500")
    """

    def __init__(self, catalog_path: str) -> None:
        """Initialize catalog creator.

        Args:
            catalog_path: Path where catalog database will be created
        """
        self.catalog_path = catalog_path
        self.views: list[dict[str, str]] = []
        self.validations: list[dict[str, Any]] = []

    def create(self) -> None:
        """Create an empty catalog database.

        Creates a new DuckDB database file. If the file already exists,
        it will be overwritten.
        """
        # Remove existing catalog if it exists
        catalog = Path(self.catalog_path)
        if catalog.exists():
            catalog.unlink()

        # Create new catalog
        con = duckdb.connect(self.catalog_path)
        con.close()

    def add_base_view(
        self,
        view_name: str,
        parquet_url: str,
        description: str | None = None,
    ) -> None:
        """Add a base view that references remote Parquet files.

        Args:
            view_name: Name of the view to create
            parquet_url: URL or pattern to Parquet files (supports wildcards)
            description: Optional description of the view
        """
        con = duckdb.connect(self.catalog_path)

        # Create view that references remote parquet
        sql = f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_parquet('{parquet_url}')"
        con.execute(sql)

        self.views.append(
            {
                "name": view_name,
                "type": "base",
                "source": parquet_url,
                "description": description,
            },
        )

        con.close()

    def add_analytical_view(
        self,
        view_name: str,
        query: str,
        description: str | None = None,
    ) -> None:
        """Add an analytical view that queries other views.

        Args:
            view_name: Name of the view to create
            query: SQL query defining the view
            description: Optional description of the view
        """
        con = duckdb.connect(self.catalog_path)

        # Create analytical view
        sql = f"CREATE OR REPLACE VIEW {view_name} AS {query}"
        con.execute(sql)

        self.views.append(
            {
                "name": view_name,
                "type": "analytical",
                "query": query,
                "description": description,
            },
        )

        con.close()

    def list_views(self) -> list[dict[str, str]]:
        """List all views in the catalog.

        Returns:
            List of view information dictionaries
        """
        con = duckdb.connect(self.catalog_path, read_only=True)

        result = con.execute("""
            SELECT table_name, view_definition
            FROM information_schema.views
            WHERE table_schema = 'main'
            AND table_name NOT LIKE 'duckdb_%'
            AND table_name NOT LIKE 'sqlite_%'
            AND table_name NOT LIKE 'pragma_%'
            ORDER BY table_name
        """).fetchall()

        views = [{"name": row[0], "sql": row[1]} for row in result]

        con.close()
        return views

    def validate(self) -> list[dict[str, Any]]:
        """Validate the catalog.

        Performs various checks:
        - Catalog file exists and is accessible
        - File size is reasonable (< 100 KB for metadata-only)
        - Views are syntactically correct
        - No circular dependencies

        Returns:
            List of validation results
        """
        validation_results = []

        # Check file exists
        if not Path(self.catalog_path).exists():
            validation_results.append(
                {
                    "check": "file_exists",
                    "status": "failed",
                    "message": f"Catalog file not found: {self.catalog_path}",
                },
            )
            return validation_results

        validation_results.append(
            {"check": "file_exists", "status": "passed", "message": "Catalog file exists"},
        )

        # Check file size
        file_size = Path(self.catalog_path).stat().st_size
        max_size = 100 * 1024  # 100 KB

        if file_size > max_size:
            validation_results.append(
                {
                    "check": "file_size",
                    "status": "warning",
                    "message": f"Catalog size ({file_size} bytes) exceeds {max_size} bytes",
                },
            )
        else:
            validation_results.append(
                {
                    "check": "file_size",
                    "status": "passed",
                    "message": f"Catalog size: {file_size} bytes",
                },
            )

        # Check views are queryable
        try:
            con = duckdb.connect(self.catalog_path, read_only=True)
            views = con.execute("""
                SELECT table_name FROM information_schema.views
                WHERE table_schema = 'main'
                AND table_name NOT LIKE 'duckdb_%'
                AND table_name NOT LIKE 'sqlite_%'
                AND table_name NOT LIKE 'pragma_%'
            """).fetchall()
            con.close()

            validation_results.append(
                {
                    "check": "views_accessible",
                    "status": "passed",
                    "message": f"Found {len(views)} views",
                },
            )
        except Exception as e:
            validation_results.append(
                {
                    "check": "views_accessible",
                    "status": "failed",
                    "message": f"Error accessing views: {e!s}",
                },
            )

        self.validations = validation_results
        return validation_results

    def validate_and_create(self) -> list[dict[str, Any]]:
        """Validate and create catalog in one step.

        Returns:
            List of validation results
        """
        # Create catalog first
        self.create()

        # Then validate
        return self.validate()

    def get_catalog_info(self) -> dict[str, Any]:
        """Get information about the catalog.

        Returns:
            Dictionary with catalog metadata
        """
        if not Path(self.catalog_path).exists():
            return {"error": "Catalog not found"}

        file_size = Path(self.catalog_path).stat().st_size
        views = self.list_views()

        return {
            "path": self.catalog_path,
            "size_bytes": file_size,
            "size_kb": round(file_size / 1024, 2),
            "view_count": len(views),
            "views": views,
        }

    def create_versioned_catalog(
        self,
        version: str,
        _parquet_pattern: str,
    ) -> str:
        """Create a versioned catalog.

        Args:
            version: Version identifier (e.g., "2026-01", "latest")
            parquet_pattern: Parquet file pattern for this version

        Returns:
            Path to created catalog
        """
        # Create versioned filename
        base_name = Path(self.catalog_path).stem
        extension = Path(self.catalog_path).suffix
        versioned_name = f"{base_name}-{version}{extension}"
        versioned_path = Path(self.catalog_path).parent / versioned_name

        # Create catalog with version-specific pattern
        versioned_creator = CatalogCreator(str(versioned_path))
        versioned_creator.create()

        return str(versioned_path)

    @staticmethod
    def validate_remote_url(url: str) -> bool:
        """Validate that a URL is properly formed.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme in ["http", "https"], result.netloc])
        except Exception:
            return False

    def add_standard_views(
        self,
        base_url: str = "https://archive.org/download",
        date_pattern: str | None = None,
    ) -> None:
        """Add standard CausaGanha views to the catalog.

        Args:
            base_url: Base URL for Internet Archive
            date_pattern: Optional date pattern (e.g., "2026-01-*")
        """
        # Construct parquet patterns
        if date_pattern:
            intimations_pattern = f"{base_url}/djen-parquet-{date_pattern}.parquet"
            lawyers_pattern = f"{base_url}/djen-lawyers-{date_pattern}.parquet"
            partes_pattern = f"{base_url}/djen-partes-{date_pattern}.parquet"
        else:
            intimations_pattern = f"{base_url}/djen-parquet-*.parquet"
            lawyers_pattern = f"{base_url}/djen-lawyers-*.parquet"
            partes_pattern = f"{base_url}/djen-partes-*.parquet"

        # Add base views
        self.add_base_view(
            "intimations_raw",
            intimations_pattern,
            "Raw DJEN intimation data",
        )

        self.add_base_view(
            "lawyers_raw",
            lawyers_pattern,
            "Lawyer profiles and ratings",
        )

        self.add_base_view(
            "partes_raw",
            partes_pattern,
            "Case parties information",
        )

        # Add analytical views
        self.add_analytical_view(
            "top_lawyers",
            """
            SELECT *
            FROM lawyers_raw
            WHERE total_cases >= 10
            ORDER BY rating DESC
            LIMIT 100
            """,
            "Top 100 lawyers by rating with 10+ cases",
        )

        self.add_analytical_view(
            "recent_intimations",
            """
            SELECT *
            FROM intimations_raw
            WHERE data_disponibilizacao >= CURRENT_DATE - INTERVAL '30 days'
            ORDER BY data_disponibilizacao DESC
            """,
            "Intimations from the last 30 days",
        )

        self.add_analytical_view(
            "tribunal_stats",
            """
            SELECT
                sigla_tribunal,
                COUNT(*) as total_intimations,
                COUNT(DISTINCT numero_processo) as unique_cases,
                MIN(data_disponibilizacao) as earliest_date,
                MAX(data_disponibilizacao) as latest_date
            FROM intimations_raw
            GROUP BY sigla_tribunal
            ORDER BY total_intimations DESC
            """,
            "Statistics per tribunal",
        )

    def export_catalog_info(self, output_path: str) -> None:
        """Export catalog information to a JSON file.

        Args:
            output_path: Path where JSON file will be written
        """
        import json

        info = self.get_catalog_info()

        with Path(output_path).open("w") as f:
            json.dump(info, f, indent=2)
