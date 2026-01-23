"""Parquet Data Lake Export Module

Exports analyzed judicial decisions from DuckDB to Parquet files
using hierarchical date+tribunal partitioning for Internet Archive.

Naming Convention: causaganha-{YYYY}-{MM}-{DD}-{TRIBUNAL}.parquet
Example: causaganha-2025-01-15-TJRO.parquet

Usage:
    exporter = ParquetExporter(db_connection, ExportConfig())
    file_path = await exporter.export_day_tribunal("2025-01-15", "TJRO")
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import ibis
import pyarrow as pa
import pyarrow.parquet as pq


logger = logging.getLogger(__name__)


@dataclass
class ExportConfig:
    """Configuration for Parquet export."""

    output_dir: Path = Path("./exports")
    compression: str = "snappy"  # Fast compression, good ratio
    row_group_size: int = 10_000  # Rows per row group
    schema_version: str = "v1"

    def __post_init__(self):
        """Ensure output directory exists."""
        self.output_dir.mkdir(parents=True, exist_ok=True)


class ParquetExporter:
    """Exports intimations from DuckDB to Parquet files."""

    def __init__(self, db_connection, config: ExportConfig | None = None):
        """Initialize Parquet exporter.

        Args:
            db_connection: Ibis DuckDB connection
            config: Export configuration (uses defaults if None)
        """
        self.db = db_connection
        self.config = config or ExportConfig()
        logger.info(
            f"ParquetExporter initialized with compression={self.config.compression}",
        )

    async def export_day_tribunal(
        self,
        partition_date: str,
        tribunal: str,
    ) -> tuple[Path, int]:
        """Export single day+tribunal partition to Parquet.

        Args:
            partition_date: Date in YYYY-MM-DD format
            tribunal: Tribunal code (e.g., TJRO, TJSP)

        Returns:
            Tuple of (file_path, row_count)

        Raises:
            ValueError: If no data found for date+tribunal
            IOError: If file write fails
        """
        logger.info(f"Exporting {tribunal} for {partition_date}")

        # Query data from DuckDB
        df = self._query_intimations(partition_date, tribunal)
        row_count = len(df)

        if row_count == 0:
            raise ValueError(
                f"No data found for tribunal={tribunal}, date={partition_date}",
            )

        logger.info(f"Found {row_count} rows to export")

        # Generate filename
        filename = self._generate_filename(partition_date, tribunal)
        file_path = self.config.output_dir / filename

        # Convert to PyArrow table
        table = self._dataframe_to_arrow(df)

        # Write Parquet file
        self._write_parquet(table, file_path)

        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        logger.info(
            f"Exported {row_count} rows to {filename} ({file_size_mb:.2f} MB)",
        )

        return file_path, row_count

    async def export_day_all_tribunals(
        self,
        partition_date: str,
    ) -> list[tuple[str, Path, int]]:
        """Export all tribunals for a single day.

        Args:
            partition_date: Date in YYYY-MM-DD format

        Returns:
            List of (tribunal, file_path, row_count) tuples

        Raises:
            ValueError: If no data found for date
        """
        logger.info(f"Exporting all tribunals for {partition_date}")

        # Get list of tribunals with data for this date
        tribunals = self._get_tribunals_for_date(partition_date)

        if not tribunals:
            raise ValueError(f"No data found for date={partition_date}")

        logger.info(f"Found {len(tribunals)} tribunals with data")

        results = []
        for tribunal in tribunals:
            try:
                file_path, row_count = await self.export_day_tribunal(
                    partition_date,
                    tribunal,
                )
                results.append((tribunal, file_path, row_count))
            except Exception as e:
                logger.error(f"Failed to export {tribunal}: {e}")
                # Continue with other tribunals
                continue

        logger.info(
            f"Successfully exported {len(results)}/{len(tribunals)} tribunals",
        )
        return results

    def _query_intimations(self, date: str, tribunal: str) -> pa.RecordBatch:
        """Query DuckDB for intimations to export.

        Args:
            date: Partition date (YYYY-MM-DD)
            tribunal: Tribunal code

        Returns:
            PyArrow RecordBatch with intimation data
        """
        # Build Ibis query
        intimations = self.db.table("intimations")
        analysis = self.db.table("decision_analysis")

        # Join intimations with analysis
        query = (
            intimations.left_join(
                analysis,
                intimations.id == analysis.intimation_id,
            )
            .filter(
                (intimations.data_disponibilizacao == date)
                & (intimations.sigla_tribunal == tribunal),
            )
            .select(
                # Intimation fields
                intimation_id=intimations.id,
                numero_processo=intimations.numero_processo,
                hash=intimations.hash,
                sigla_tribunal=intimations.sigla_tribunal,
                nome_orgao=intimations.nome_orgao,
                data_disponibilizacao=intimations.data_disponibilizacao,
                texto=intimations.texto,
                tipo_documento=intimations.tipo_documento,
                nome_classe=intimations.nome_classe,
                # Analysis fields (nullable if not analyzed)
                winner_lawyer_oab=analysis.winner_lawyer_oab,
                winner_lawyer_state=analysis.winner_lawyer_state,
                loser_lawyer_oab=analysis.loser_lawyer_oab,
                loser_lawyer_state=analysis.loser_lawyer_state,
                decision_type=analysis.decision_type,
                outcome=analysis.outcome,
                judge_name=analysis.judge_name,
                confidence_score=analysis.confidence_score,
                analyzed_at=analysis.created_at,
                analysis_method=analysis.analysis_method,
                # Partition columns for efficient filtering
                partition_date=intimations.data_disponibilizacao,
                year=ibis._.data_disponibilizacao.year(),
                month=ibis._.data_disponibilizacao.month(),
                day=ibis._.data_disponibilizacao.day(),
            )
        )

        # Execute and convert to PyArrow
        return query.to_pyarrow()

    def _get_tribunals_for_date(self, date: str) -> list[str]:
        """Get list of tribunals with data for a specific date.

        Args:
            date: Partition date (YYYY-MM-DD)

        Returns:
            List of tribunal codes
        """
        intimations = self.db.table("intimations")

        tribunals_query = (
            intimations.filter(intimations.data_disponibilizacao == date)
            .select(intimations.sigla_tribunal)
            .distinct()
            .order_by(intimations.sigla_tribunal)
        )

        result = tribunals_query.execute()
        return result["sigla_tribunal"].tolist()

    def _dataframe_to_arrow(self, df: pa.Table) -> pa.Table:
        """Convert data to PyArrow table with proper schema.

        Args:
            df: PyArrow Table from query (to_pyarrow() returns Table, not RecordBatch)

        Returns:
            PyArrow Table with validated schema
        """
        # The df is already a Table (not RecordBatch), just return it
        # to_pyarrow() from Ibis returns a Table directly
        return df

    def _build_parquet_schema(self) -> pa.Schema:
        """Define Parquet schema with nested structures.

        Returns:
            PyArrow schema for Parquet export
        """
        return pa.schema(
            [
                # Identifiers
                ("intimation_id", pa.int64()),
                ("numero_processo", pa.string()),
                ("hash", pa.string()),
                # Court metadata
                ("sigla_tribunal", pa.string()),
                ("nome_orgao", pa.string()),
                ("data_disponibilizacao", pa.date32()),
                # Decision text (from PJe API)
                ("texto", pa.string()),
                ("tipo_documento", pa.string()),
                ("nome_classe", pa.string()),
                # LLM/RAG Analysis results (nullable)
                ("winner_lawyer_oab", pa.string()),
                ("winner_lawyer_state", pa.string()),
                ("loser_lawyer_oab", pa.string()),
                ("loser_lawyer_state", pa.string()),
                ("decision_type", pa.string()),
                ("outcome", pa.string()),
                ("judge_name", pa.string()),
                ("confidence_score", pa.float64()),
                # Processing metadata
                ("analyzed_at", pa.timestamp("us")),
                ("analysis_method", pa.string()),
                # Partition columns
                ("partition_date", pa.date32()),
                ("year", pa.int32()),
                ("month", pa.int32()),
                ("day", pa.int32()),
            ],
        )

    def _write_parquet(self, table: pa.Table, file_path: Path) -> None:
        """Write PyArrow table to Parquet file.

        Args:
            table: PyArrow table to write
            file_path: Output file path

        Raises:
            IOError: If write fails
        """
        pq.write_table(
            table,
            file_path,
            compression=self.config.compression,
            row_group_size=self.config.row_group_size,
            # Enable statistics for query optimization
            write_statistics=True,
            # Store schema in metadata
            store_schema=True,
            # Version 2.6 for better compression
            version="2.6",
        )

        logger.debug(f"Wrote Parquet file: {file_path}")

    def _generate_filename(self, date: str, tribunal: str) -> str:
        """Generate Parquet filename following naming convention.

        Args:
            date: Partition date (YYYY-MM-DD)
            tribunal: Tribunal code

        Returns:
            Filename: causaganha-{YYYY}-{MM}-{DD}-{TRIBUNAL}.parquet
        """
        return f"causaganha-{date}-{tribunal}.parquet"

    @staticmethod
    def get_yesterday() -> str:
        """Get yesterday's date in YYYY-MM-DD format."""
        yesterday = datetime.now() - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d")
