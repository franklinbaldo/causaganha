"""Parquet-Based Analysis Pipeline

Analyzes judicial decisions from parquet files (local or Internet Archive).
Supports all analysis strategies (LLM/RAG/Hybrid) and multiple output modes.

Usage:
    # Analyze from local parquet file
    results = await analyze_from_parquet(
        parquet_path="./cache/causaganha-2025-01-15-TJRO.parquet",
        strategy=AnalysisStrategy.HYBRID,
        output_mode="parquet"
    )

    # Analyze from Internet Archive
    results = await analyze_from_ia(
        tribunal="TJRO",
        date="2025-01-15",
        strategy=AnalysisStrategy.HYBRID
    )
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import structlog

from causaganha.v2.analysis.analyzer import DecisionAnalyzer
from causaganha.v2.analysis.hybrid_analyzer import HybridAnalyzer
from causaganha.v2.analysis.models import DecisionAnalysis
from causaganha.v2.analysis.rag_analyzer import RAGAnalyzer
from causaganha.v2.analysis.strategy import AnalysisStrategy
from causaganha.v2.pipeline.ia_download import IAParquetDownloader
from causaganha.v2.storage.connection import get_connection
from causaganha.v2.storage.queries import store_analysis


logger = structlog.get_logger()


class OutputMode(str, Enum):
    """Output mode for analysis results."""

    PARQUET = "parquet"  # Write to new parquet file
    DUCKDB = "duckdb"  # Write to DuckDB database
    BOTH = "both"  # Write to both parquet and DuckDB
    NONE = "none"  # Return results only (no persistence)


@dataclass
class ParquetAnalysisConfig:
    """Configuration for parquet-based analysis."""

    batch_size: int = 10  # Number of decisions to analyze at once
    filter_unanalyzed: bool = True  # Only analyze rows without analysis
    reanalyze_low_confidence: bool = False  # Reanalyze low confidence decisions
    confidence_threshold: float = 0.70  # Threshold for reanalysis
    output_mode: OutputMode = OutputMode.PARQUET  # Where to write results
    output_dir: Path = Path("./analysis_results")  # Output directory for parquet
    max_decisions: int | None = None  # Max decisions to analyze (None = all)

    def __post_init__(self):
        """Ensure output directory exists."""
        if self.output_mode in (OutputMode.PARQUET, OutputMode.BOTH):
            self.output_dir.mkdir(parents=True, exist_ok=True)


class ParquetAnalyzer:
    """Analyzes judicial decisions from parquet files."""

    def __init__(
        self,
        config: ParquetAnalysisConfig | None = None,
        ia_downloader: IAParquetDownloader | None = None,
    ):
        """Initialize parquet analyzer.

        Args:
            config: Analysis configuration (uses defaults if None)
            ia_downloader: IA downloader instance (creates new if None)
        """
        self.config = config or ParquetAnalysisConfig()
        self.ia_downloader = ia_downloader or IAParquetDownloader()
        logger.info(
            "ParquetAnalyzer initialized",
            batch_size=self.config.batch_size,
            output_mode=self.config.output_mode.value,
        )

    async def analyze_from_parquet(
        self,
        parquet_path: Path | str,
        strategy: AnalysisStrategy | str = AnalysisStrategy.HYBRID,
        confidence_threshold: float = 0.70,
    ) -> dict[str, Any]:
        """Analyze decisions from a local parquet file.

        Args:
            parquet_path: Path to parquet file
            strategy: Analysis strategy (llm, rag, hybrid, auto)
            confidence_threshold: Confidence threshold for hybrid strategy

        Returns:
            Dictionary with analysis statistics
        """
        if isinstance(strategy, str):
            strategy = AnalysisStrategy(strategy)

        parquet_path = Path(parquet_path)

        if not parquet_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

        logger.info(
            "analyze_from_parquet_start",
            file=str(parquet_path),
            strategy=strategy.value,
        )

        # Read parquet file
        table = pq.read_table(parquet_path)
        logger.info(f"Loaded {len(table)} rows from parquet")

        # Filter decisions to analyze
        decisions_to_analyze = self._filter_decisions(table)

        if not decisions_to_analyze:
            logger.info("No decisions to analyze after filtering")
            return {
                "analyzed": 0,
                "failed": 0,
                "skipped": len(table),
                "status": "success",
            }

        logger.info(
            f"Filtered to {len(decisions_to_analyze)} decisions to analyze "
            f"(from {len(table)} total)",
        )

        # Initialize analyzer
        analyzer = await self._initialize_analyzer(strategy, confidence_threshold)

        # Process decisions in batches
        results = await self._process_decisions(
            decisions_to_analyze,
            analyzer,
            strategy,
        )

        # Write results based on output mode
        if self.config.output_mode in (OutputMode.PARQUET, OutputMode.BOTH):
            output_path = await self._write_parquet_results(
                parquet_path,
                table,
                results,
            )
            results["output_file"] = str(output_path)

        if self.config.output_mode in (OutputMode.DUCKDB, OutputMode.BOTH):
            await self._write_duckdb_results(results)

        logger.info(
            "analyze_from_parquet_complete",
            analyzed=results["analyzed"],
            failed=results["failed"],
        )

        return results

    async def analyze_from_ia(
        self,
        tribunal: str,
        date: str,
        strategy: AnalysisStrategy | str = AnalysisStrategy.HYBRID,
        confidence_threshold: float = 0.70,
        auto_download: bool = True,
    ) -> dict[str, Any]:
        """Analyze decisions from Internet Archive.

        Args:
            tribunal: Tribunal code (e.g., TJRO)
            date: Date in YYYY-MM-DD format
            strategy: Analysis strategy
            confidence_threshold: Confidence threshold for hybrid
            auto_download: Automatically download if not cached

        Returns:
            Dictionary with analysis statistics
        """
        logger.info(
            "analyze_from_ia_start",
            tribunal=tribunal,
            date=date,
            strategy=strategy.value if isinstance(strategy, AnalysisStrategy) else strategy,
        )

        # Download parquet file (or use cached)
        parquet_path = await self.ia_downloader.download(
            tribunal=tribunal,
            date=date,
            force_refresh=not auto_download,
        )

        # Analyze using local parquet
        return await self.analyze_from_parquet(
            parquet_path=parquet_path,
            strategy=strategy,
            confidence_threshold=confidence_threshold,
        )

    async def analyze_date_range(
        self,
        start_date: str,
        end_date: str,
        tribunal: str,
        strategy: AnalysisStrategy | str = AnalysisStrategy.HYBRID,
        confidence_threshold: float = 0.70,
    ) -> dict[str, Any]:
        """Analyze decisions from Internet Archive for a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            tribunal: Tribunal code
            strategy: Analysis strategy
            confidence_threshold: Confidence threshold for hybrid

        Returns:
            Aggregated statistics for all dates
        """
        logger.info(
            "analyze_date_range_start",
            start_date=start_date,
            end_date=end_date,
            tribunal=tribunal,
        )

        # Download parquet files for date range
        parquet_files = await self.ia_downloader.download_range(
            start_date=start_date,
            end_date=end_date,
            tribunal=tribunal,
            skip_missing=True,
        )

        # Analyze each file
        total_analyzed = 0
        total_failed = 0
        total_skipped = 0
        output_files = []

        for parquet_path in parquet_files:
            try:
                results = await self.analyze_from_parquet(
                    parquet_path=parquet_path,
                    strategy=strategy,
                    confidence_threshold=confidence_threshold,
                )

                total_analyzed += results.get("analyzed", 0)
                total_failed += results.get("failed", 0)
                total_skipped += results.get("skipped", 0)

                if "output_file" in results:
                    output_files.append(results["output_file"])

            except Exception as e:
                logger.error(
                    "analyze_file_failed",
                    file=str(parquet_path),
                    error=str(e),
                )
                total_failed += 1

        logger.info(
            "analyze_date_range_complete",
            files_processed=len(parquet_files),
            analyzed=total_analyzed,
            failed=total_failed,
            skipped=total_skipped,
        )

        return {
            "files_processed": len(parquet_files),
            "analyzed": total_analyzed,
            "failed": total_failed,
            "skipped": total_skipped,
            "output_files": output_files,
            "status": "success",
        }

    def _filter_decisions(self, table: pa.Table) -> list[dict]:
        """Filter decisions that need analysis.

        Args:
            table: PyArrow table from parquet

        Returns:
            List of decision dictionaries to analyze
        """
        decisions = []

        for i in range(len(table)):
            row = {col: table[col][i].as_py() for col in table.column_names}

            # Skip if max decisions reached
            if self.config.max_decisions and len(decisions) >= self.config.max_decisions:
                break

            # Filter based on configuration
            should_analyze = False

            if self.config.filter_unanalyzed:
                # Analyze if no analysis exists
                if row.get("outcome") is None or row.get("confidence_score") is None:
                    should_analyze = True

            if self.config.reanalyze_low_confidence:
                # Analyze if confidence is below threshold
                confidence = row.get("confidence_score")
                if confidence is not None and confidence < self.config.confidence_threshold:
                    should_analyze = True

            if not self.config.filter_unanalyzed and not self.config.reanalyze_low_confidence:
                # If no filters, analyze everything
                should_analyze = True

            if should_analyze:
                decisions.append(row)

        return decisions

    async def _initialize_analyzer(
        self,
        strategy: AnalysisStrategy,
        confidence_threshold: float,
    ) -> Any:
        """Initialize the appropriate analyzer based on strategy."""
        if strategy == AnalysisStrategy.LLM:
            logger.info("using_llm_only_strategy")
            return DecisionAnalyzer()

        if strategy == AnalysisStrategy.RAG:
            logger.info("using_rag_only_strategy")
            return await RAGAnalyzer.create()

        # HYBRID or AUTO
        logger.info(
            "using_hybrid_strategy",
            confidence_threshold=confidence_threshold,
        )
        rag_analyzer = await RAGAnalyzer.create()
        llm_analyzer = DecisionAnalyzer()
        return HybridAnalyzer(rag_analyzer, llm_analyzer, confidence_threshold)

    async def _process_decisions(
        self,
        decisions: list[dict],
        analyzer: Any,
        strategy: AnalysisStrategy,
    ) -> dict[str, Any]:
        """Process decisions in batches.

        Args:
            decisions: List of decision dictionaries
            analyzer: Initialized analyzer
            strategy: Analysis strategy

        Returns:
            Analysis results with statistics
        """
        total_analyzed = 0
        total_failed = 0
        analyses_by_id = {}  # Map intimation_id to analysis result

        usage_stats = {
            "rag_used": 0,
            "llm_used": 0,
            "total_cost": 0.0,
        }

        # Process in batches
        for i in range(0, len(decisions), self.config.batch_size):
            batch = decisions[i : i + self.config.batch_size]

            logger.info(
                f"Processing batch {i // self.config.batch_size + 1} "
                f"({len(batch)} decisions)",
            )

            intimation_ids = [d["intimation_id"] for d in batch]
            pdf_urls = [d.get("link") for d in batch]
            texts = [d.get("texto", "") for d in batch]

            try:
                analyses = []

                if strategy == AnalysisStrategy.LLM:
                    analyses = await analyzer.analyze_batch(pdf_urls, intimation_ids)
                    usage_stats["llm_used"] += len(analyses)
                    usage_stats["total_cost"] += len(analyses) * 0.000420

                elif strategy == AnalysisStrategy.RAG:
                    analyses = await analyzer.analyze_batch(texts, intimation_ids)
                    usage_stats["rag_used"] += len(analyses)
                    usage_stats["total_cost"] += len(analyses) * 0.000008

                else:  # HYBRID
                    analyses, batch_stats = await analyzer.analyze_batch(
                        texts,
                        intimation_ids,
                        pdf_urls,
                    )
                    usage_stats["rag_used"] += batch_stats.get("rag_used", 0)
                    usage_stats["llm_used"] += batch_stats.get("llm_used", 0)
                    usage_stats["total_cost"] += batch_stats.get("total_cost", 0.0)

                # Store results
                for result, intimation_id in zip(analyses, intimation_ids, strict=True):
                    if not isinstance(result, Exception):
                        analyses_by_id[intimation_id] = result
                        total_analyzed += 1
                    else:
                        logger.error(
                            "analysis_failed",
                            intimation_id=intimation_id,
                            error=str(result),
                        )
                        total_failed += 1

            except Exception as e:
                logger.exception("batch_failed", error=str(e))
                total_failed += len(batch)

        return {
            "analyzed": total_analyzed,
            "failed": total_failed,
            "skipped": len(decisions) - total_analyzed - total_failed,
            "analyses": analyses_by_id,
            **usage_stats,
            "status": "success",
        }

    async def _write_parquet_results(
        self,
        original_path: Path,
        original_table: pa.Table,
        results: dict[str, Any],
    ) -> Path:
        """Write analysis results to a new parquet file.

        Args:
            original_path: Path to original parquet file
            original_table: Original PyArrow table
            results: Analysis results

        Returns:
            Path to output parquet file
        """
        analyses = results["analyses"]

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = original_path.stem + f"_analyzed_{timestamp}.parquet"
        output_path = self.config.output_dir / output_filename

        logger.info(f"Writing results to {output_path}")

        # Create updated columns
        updated_columns = {}

        for col_name in original_table.column_names:
            updated_columns[col_name] = original_table[col_name]

        # Update analysis columns
        for i in range(len(original_table)):
            intimation_id = original_table["intimation_id"][i].as_py()

            if intimation_id in analyses:
                analysis: DecisionAnalysis = analyses[intimation_id]

                # Update analysis fields
                if "winner_lawyer_oab" not in updated_columns:
                    updated_columns["winner_lawyer_oab"] = [None] * len(original_table)
                updated_columns["winner_lawyer_oab"][i] = analysis.winner_lawyer_oab

                if "winner_lawyer_state" not in updated_columns:
                    updated_columns["winner_lawyer_state"] = [None] * len(original_table)
                updated_columns["winner_lawyer_state"][i] = analysis.winner_lawyer_state

                if "loser_lawyer_oab" not in updated_columns:
                    updated_columns["loser_lawyer_oab"] = [None] * len(original_table)
                updated_columns["loser_lawyer_oab"][i] = analysis.loser_lawyer_oab

                if "loser_lawyer_state" not in updated_columns:
                    updated_columns["loser_lawyer_state"] = [None] * len(original_table)
                updated_columns["loser_lawyer_state"][i] = analysis.loser_lawyer_state

                if "outcome" not in updated_columns:
                    updated_columns["outcome"] = [None] * len(original_table)
                updated_columns["outcome"][i] = analysis.outcome.value

                if "decision_type" not in updated_columns:
                    updated_columns["decision_type"] = [None] * len(original_table)
                updated_columns["decision_type"][i] = (
                    analysis.decision_type.value if analysis.decision_type else None
                )

                if "confidence_score" not in updated_columns:
                    updated_columns["confidence_score"] = [None] * len(original_table)
                updated_columns["confidence_score"][i] = analysis.confidence_score

                if "analyzed_at" not in updated_columns:
                    updated_columns["analyzed_at"] = [None] * len(original_table)
                updated_columns["analyzed_at"][i] = datetime.now()

        # Convert to PyArrow table (use original schema if possible)
        updated_table = pa.Table.from_pydict(updated_columns)

        # Write to parquet
        pq.write_table(
            updated_table,
            output_path,
            compression="snappy",
            write_statistics=True,
            store_schema=True,
            version="2.6",
        )

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(
            f"Wrote {len(updated_table)} rows to {output_filename} ({file_size_mb:.2f} MB)",
        )

        return output_path

    async def _write_duckdb_results(self, results: dict[str, Any]) -> None:
        """Write analysis results to DuckDB.

        Args:
            results: Analysis results with analyses dictionary
        """
        analyses = results["analyses"]
        con = get_connection()

        logger.info(f"Writing {len(analyses)} analyses to DuckDB")

        for intimation_id, analysis in analyses.items():
            try:
                store_analysis(con, intimation_id, analysis)
            except Exception as e:
                logger.error(
                    "store_failed",
                    intimation_id=intimation_id,
                    error=str(e),
                )

        logger.info("DuckDB write complete")


# Convenience functions for common use cases


async def analyze_from_parquet(
    parquet_path: Path | str,
    strategy: AnalysisStrategy | str = AnalysisStrategy.HYBRID,
    output_mode: OutputMode | str = OutputMode.PARQUET,
    confidence_threshold: float = 0.70,
    filter_unanalyzed: bool = True,
) -> dict[str, Any]:
    """Analyze decisions from a parquet file.

    Args:
        parquet_path: Path to parquet file
        strategy: Analysis strategy (llm, rag, hybrid, auto)
        output_mode: Where to write results (parquet, duckdb, both, none)
        confidence_threshold: Confidence threshold for hybrid
        filter_unanalyzed: Only analyze rows without analysis

    Returns:
        Analysis statistics
    """
    if isinstance(output_mode, str):
        output_mode = OutputMode(output_mode)

    config = ParquetAnalysisConfig(
        output_mode=output_mode,
        filter_unanalyzed=filter_unanalyzed,
        confidence_threshold=confidence_threshold,
    )

    analyzer = ParquetAnalyzer(config=config)
    return await analyzer.analyze_from_parquet(
        parquet_path=parquet_path,
        strategy=strategy,
        confidence_threshold=confidence_threshold,
    )


async def analyze_from_ia(
    tribunal: str,
    date: str,
    strategy: AnalysisStrategy | str = AnalysisStrategy.HYBRID,
    output_mode: OutputMode | str = OutputMode.PARQUET,
    confidence_threshold: float = 0.70,
) -> dict[str, Any]:
    """Analyze decisions from Internet Archive.

    Args:
        tribunal: Tribunal code (e.g., TJRO)
        date: Date in YYYY-MM-DD format
        strategy: Analysis strategy
        output_mode: Where to write results
        confidence_threshold: Confidence threshold for hybrid

    Returns:
        Analysis statistics
    """
    if isinstance(output_mode, str):
        output_mode = OutputMode(output_mode)

    config = ParquetAnalysisConfig(output_mode=output_mode)
    analyzer = ParquetAnalyzer(config=config)

    return await analyzer.analyze_from_ia(
        tribunal=tribunal,
        date=date,
        strategy=strategy,
        confidence_threshold=confidence_threshold,
    )
