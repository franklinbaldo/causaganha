"""Tests for Parquet-Based Analysis Pipeline."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pyarrow as pa
import pyarrow.parquet as pq

from causaganha.v2.pipeline.analyze_parquet import (
    ParquetAnalyzer,
    ParquetAnalysisConfig,
    OutputMode,
)
from causaganha.v2.analysis.strategy import AnalysisStrategy
from causaganha.v2.analysis.models import DecisionAnalysis, Outcome, DecisionType


@pytest.fixture
def analysis_config(tmp_path):
    """Create test analysis config."""
    return ParquetAnalysisConfig(
        batch_size=5,
        filter_unanalyzed=True,
        output_mode=OutputMode.NONE,
        output_dir=tmp_path / "output",
        max_decisions=10,
    )


@pytest.fixture
def sample_parquet(tmp_path):
    """Create sample parquet file for testing."""
    # Create sample data
    data = {
        "intimation_id": [1, 2, 3, 4, 5],
        "numero_processo": ["1001", "1002", "1003", "1004", "1005"],
        "hash": ["hash1", "hash2", "hash3", "hash4", "hash5"],
        "sigla_tribunal": ["TJRO"] * 5,
        "nome_orgao": ["Vara 1"] * 5,
        "data_disponibilizacao": ["2025-01-15"] * 5,
        "texto": [
            "Decisão sobre caso 1",
            "Decisão sobre caso 2",
            "Decisão sobre caso 3",
            "Decisão sobre caso 4",
            "Decisão sobre caso 5",
        ],
        "link": [f"http://example.com/pdf{i}.pdf" for i in range(1, 6)],
        "tipo_documento": ["SENTENÇA"] * 5,
        "nome_classe": ["Ação Civil"] * 5,
        # Analysis fields (some populated, some null)
        "winner_lawyer_oab": ["12345", None, "23456", None, None],
        "winner_lawyer_state": ["RO", None, "RO", None, None],
        "loser_lawyer_oab": ["54321", None, "65432", None, None],
        "loser_lawyer_state": ["RO", None, "RO", None, None],
        "decision_type": ["sentença", None, "sentença", None, None],
        "outcome": ["procedente", None, "improcedente", None, None],
        "confidence_score": [0.9, None, 0.85, None, None],
        "analyzed_at": [None, None, None, None, None],
        "analysis_method": ["hybrid", None, "rag", None, None],
        "partition_date": ["2025-01-15"] * 5,
        "year": [2025] * 5,
        "month": [1] * 5,
        "day": [15] * 5,
    }

    # Create PyArrow table
    table = pa.Table.from_pydict(data)

    # Write to parquet
    parquet_path = tmp_path / "test_data.parquet"
    pq.write_table(table, parquet_path)

    return parquet_path


@pytest.fixture
def analyzer(analysis_config):
    """Create analyzer instance."""
    return ParquetAnalyzer(config=analysis_config)


class TestParquetAnalysisConfig:
    """Test suite for ParquetAnalysisConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = ParquetAnalysisConfig()
        assert config.batch_size == 10
        assert config.filter_unanalyzed is True
        assert config.output_mode == OutputMode.PARQUET
        assert config.confidence_threshold == 0.70

    def test_custom_config(self, tmp_path):
        """Test custom configuration."""
        output_dir = tmp_path / "custom_output"
        config = ParquetAnalysisConfig(
            batch_size=20,
            filter_unanalyzed=False,
            output_mode=OutputMode.DUCKDB,
            output_dir=output_dir,
            confidence_threshold=0.80,
        )
        assert config.batch_size == 20
        assert config.filter_unanalyzed is False
        assert config.output_mode == OutputMode.DUCKDB
        assert config.confidence_threshold == 0.80
        assert output_dir.exists()


class TestParquetAnalyzer:
    """Test suite for ParquetAnalyzer."""

    def test_init(self, analyzer, analysis_config):
        """Test analyzer initialization."""
        assert analyzer.config == analysis_config
        assert analyzer.ia_downloader is not None

    def test_filter_decisions_unanalyzed(self, analyzer, sample_parquet):
        """Test filtering for unanalyzed decisions."""
        table = pq.read_table(sample_parquet)
        decisions = analyzer._filter_decisions(table)

        # Should return only decisions without analysis (IDs 2, 4, 5)
        assert len(decisions) == 3
        assert decisions[0]["intimation_id"] == 2
        assert decisions[1]["intimation_id"] == 4
        assert decisions[2]["intimation_id"] == 5

    def test_filter_decisions_all(self, analyzer, sample_parquet):
        """Test filtering all decisions."""
        analyzer.config.filter_unanalyzed = False
        analyzer.config.reanalyze_low_confidence = False

        table = pq.read_table(sample_parquet)
        decisions = analyzer._filter_decisions(table)

        # Should return all decisions
        assert len(decisions) == 5

    def test_filter_decisions_max_limit(self, analyzer, sample_parquet):
        """Test max decisions limit."""
        analyzer.config.filter_unanalyzed = False
        analyzer.config.max_decisions = 2

        table = pq.read_table(sample_parquet)
        decisions = analyzer._filter_decisions(table)

        # Should return only 2 decisions
        assert len(decisions) == 2

    def test_filter_decisions_low_confidence(self, analyzer, sample_parquet):
        """Test filtering for low confidence decisions."""
        analyzer.config.filter_unanalyzed = False
        analyzer.config.reanalyze_low_confidence = True
        analyzer.config.confidence_threshold = 0.87

        table = pq.read_table(sample_parquet)
        decisions = analyzer._filter_decisions(table)

        # Should return decision with confidence < 0.87 (ID 3: 0.85)
        # Plus unanalyzed (IDs 2, 4, 5)
        assert len(decisions) >= 1
        confidence_scores = [d.get("confidence_score") for d in decisions]
        assert any(c is not None and c < 0.87 for c in confidence_scores)

    @pytest.mark.asyncio
    async def test_analyze_from_parquet_file_not_found(self, analyzer):
        """Test analyze with non-existent file."""
        with pytest.raises(FileNotFoundError):
            await analyzer.analyze_from_parquet(
                parquet_path="nonexistent.parquet",
                strategy=AnalysisStrategy.HYBRID,
            )

    @pytest.mark.asyncio
    async def test_analyze_from_parquet_no_decisions(self, analyzer, tmp_path):
        """Test analyze when no decisions need analysis."""
        # Create parquet with all analyzed decisions
        data = {
            "intimation_id": [1, 2],
            "numero_processo": ["1001", "1002"],
            "hash": ["hash1", "hash2"],
            "sigla_tribunal": ["TJRO"] * 2,
            "nome_orgao": ["Vara 1"] * 2,
            "data_disponibilizacao": ["2025-01-15"] * 2,
            "texto": ["Decisão 1", "Decisão 2"],
            "link": ["http://example.com/pdf1.pdf"] * 2,
            "tipo_documento": ["SENTENÇA"] * 2,
            "nome_classe": ["Ação Civil"] * 2,
            "winner_lawyer_oab": ["12345", "23456"],
            "winner_lawyer_state": ["RO", "RO"],
            "loser_lawyer_oab": ["54321", "65432"],
            "loser_lawyer_state": ["RO", "RO"],
            "decision_type": ["sentença", "sentença"],
            "outcome": ["procedente", "improcedente"],
            "confidence_score": [0.9, 0.85],
            "analyzed_at": [None, None],
            "analysis_method": ["hybrid", "rag"],
            "partition_date": ["2025-01-15"] * 2,
            "year": [2025] * 2,
            "month": [1] * 2,
            "day": [15] * 2,
        }

        table = pa.Table.from_pydict(data)
        parquet_path = tmp_path / "all_analyzed.parquet"
        pq.write_table(table, parquet_path)

        results = await analyzer.analyze_from_parquet(
            parquet_path=parquet_path,
            strategy=AnalysisStrategy.HYBRID,
        )

        assert results["analyzed"] == 0
        assert results["skipped"] == 2
        assert results["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_item_url(self, analyzer):
        """Test IA item URL generation."""
        url = await analyzer.ia_downloader.get_item_url("TJRO", "2025-01-15")
        assert url == "https://archive.org/details/causaganha-2025-01-15-TJRO"


class TestOutputMode:
    """Test suite for OutputMode enum."""

    def test_output_modes(self):
        """Test output mode enum values."""
        assert OutputMode.PARQUET.value == "parquet"
        assert OutputMode.DUCKDB.value == "duckdb"
        assert OutputMode.BOTH.value == "both"
        assert OutputMode.NONE.value == "none"

    def test_output_mode_from_string(self):
        """Test creating output mode from string."""
        mode = OutputMode("parquet")
        assert mode == OutputMode.PARQUET

        mode = OutputMode("duckdb")
        assert mode == OutputMode.DUCKDB
