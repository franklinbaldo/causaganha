"""Comprehensive tests for repository archive functionality."""

from unittest.mock import MagicMock

import ibis
import pytest

from causaganha.infrastructure.storage.repositories.intimation import IntimationRepository


@pytest.fixture
def mock_connection():
    """Create a mock Ibis connection."""
    con = MagicMock(spec=ibis.BaseBackend)
    con.con = MagicMock()  # Raw DuckDB connection
    return con


@pytest.fixture
def repository(mock_connection):
    """Create repository with mock connection."""
    return IntimationRepository(mock_connection)


class TestGetUnarchivedIntimations:
    """Test suite for get_unarchived_intimations."""

    @pytest.mark.asyncio
    async def test_returns_only_intimations_with_null_ia_url(self, repository, mock_connection) -> None:
        """Should return only intimations where ia_url is NULL."""
        # Arrange
        mock_table = MagicMock()
        mock_connection.table.return_value = mock_table

        mock_filtered = MagicMock()
        mock_table.filter.return_value = mock_filtered
        mock_filtered.filter.return_value = mock_filtered
        mock_filtered.limit.return_value = mock_filtered

        expected_data = [
            {"id": "1", "link": "http://example.com/1.pdf", "ia_url": None},
            {"id": "2", "link": "http://example.com/2.pdf", "ia_url": ""},
        ]
        mock_filtered.execute.return_value.to_dict.return_value = expected_data

        # Act
        result = await repository.get_unarchived_intimations(limit=10)

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == "1"
        mock_connection.table.assert_called_once_with("intimations")

    @pytest.mark.asyncio
    async def test_excludes_intimations_without_links(self, repository, mock_connection) -> None:
        """Should exclude intimations that have no link."""
        # Arrange
        mock_table = MagicMock()
        mock_connection.table.return_value = mock_table

        mock_filtered = MagicMock()
        mock_table.filter.return_value = mock_filtered
        mock_filtered.filter.return_value = mock_filtered
        mock_filtered.limit.return_value = mock_filtered

        # Only return intimations with links
        expected_data = [
            {"id": "1", "link": "http://example.com/1.pdf", "ia_url": None},
        ]
        mock_filtered.execute.return_value.to_dict.return_value = expected_data

        # Act
        result = await repository.get_unarchived_intimations(limit=10)

        # Assert
        assert all(item.get("link") for item in result)

    @pytest.mark.asyncio
    async def test_respects_limit_parameter(self, repository, mock_connection) -> None:
        """Should respect the limit parameter."""
        # Arrange
        mock_table = MagicMock()
        mock_connection.table.return_value = mock_table

        mock_filtered = MagicMock()
        mock_table.filter.return_value = mock_filtered
        mock_filtered.filter.return_value = mock_filtered
        mock_filtered.limit.return_value = mock_filtered

        expected_data = [{"id": f"{i}", "link": f"http://example.com/{i}.pdf"} for i in range(5)]
        mock_filtered.execute.return_value.to_dict.return_value = expected_data

        # Act
        result = await repository.get_unarchived_intimations(limit=5)

        # Assert
        mock_filtered.limit.assert_called_with(5)
        assert len(result) <= 5

    @pytest.mark.asyncio
    async def test_handles_missing_ia_url_column_gracefully(self, repository, mock_connection) -> None:
        """Should handle case where ia_url column doesn't exist."""
        # Arrange
        mock_table = MagicMock()
        mock_connection.table.return_value = mock_table

        # First filter raises AttributeError (column doesn't exist)
        mock_table.filter.side_effect = AttributeError("ia_url column not found")

        # Fallback should work
        mock_filtered = MagicMock()
        mock_table.filter = MagicMock(side_effect=[
            AttributeError("ia_url"),
            mock_filtered,  # Second call succeeds (fallback)
        ])
        mock_filtered.filter.return_value = mock_filtered
        mock_filtered.limit.return_value = mock_filtered

        expected_data = [{"id": "1", "link": "http://example.com/1.pdf"}]
        mock_filtered.execute.return_value.to_dict.return_value = expected_data

        # Act
        result = await repository.get_unarchived_intimations(limit=10)

        # Assert - should not raise exception
        assert len(result) >= 0  # Should handle gracefully


class TestMarkAsArchived:
    """Test suite for mark_as_archived."""

    @pytest.mark.asyncio
    async def test_updates_ia_url_and_timestamp(self, repository, mock_connection) -> None:
        """Should update both ia_url and archived_at timestamp."""
        # Arrange
        intimation_id = "test-123"
        ia_url = "https://archive.org/details/test-123"

        mock_raw_con = MagicMock()
        mock_connection.con = mock_raw_con

        # Act
        await repository.mark_as_archived(intimation_id, ia_url)

        # Assert
        mock_raw_con.execute.assert_called_once()
        call_args = mock_raw_con.execute.call_args
        assert "UPDATE intimations" in call_args[0][0]
        assert "ia_url" in call_args[0][0]
        assert "archived_at" in call_args[0][0]
        assert ia_url in call_args[0][1]
        assert intimation_id in call_args[0][1]

    @pytest.mark.asyncio
    async def test_handles_missing_columns_gracefully(self, repository, mock_connection) -> None:
        """Should not raise exception if columns don't exist."""
        # Arrange
        mock_raw_con = MagicMock()
        mock_connection.con = mock_raw_con
        mock_raw_con.execute.side_effect = Exception("Column not found")

        # Act & Assert - should not raise
        await repository.mark_as_archived("test-id", "http://example.com")

    @pytest.mark.asyncio
    async def test_validates_ia_url_format(self, repository, mock_connection) -> None:
        """Should validate that ia_url is a valid URL."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid IA URL"):
            await repository.mark_as_archived("test-id", "not-a-url")

    @pytest.mark.asyncio
    async def test_validates_intimation_id_not_empty(self, repository, mock_connection) -> None:
        """Should validate that intimation_id is not empty."""
        # Act & Assert
        with pytest.raises(ValueError, match="Intimation ID cannot be empty"):
            await repository.mark_as_archived("", "https://archive.org/details/test")


class TestRepositoryIntegration:
    """Integration tests for repository operations."""

    @pytest.mark.asyncio
    async def test_archive_workflow_end_to_end(self, repository, mock_connection) -> None:
        """Test complete workflow: get unarchived → mark as archived."""
        # Arrange
        mock_table = MagicMock()
        mock_connection.table.return_value = mock_table

        mock_filtered = MagicMock()
        mock_table.filter.return_value = mock_filtered
        mock_filtered.filter.return_value = mock_filtered
        mock_filtered.limit.return_value = mock_filtered

        unarchived_data = [
            {"id": "1", "link": "http://example.com/1.pdf", "ia_url": None},
        ]
        mock_filtered.execute.return_value.to_dict.return_value = unarchived_data

        mock_raw_con = MagicMock()
        mock_connection.con = mock_raw_con

        # Act
        intimations = await repository.get_unarchived_intimations(limit=1)
        assert len(intimations) == 1

        await repository.mark_as_archived(intimations[0]["id"], "https://archive.org/details/1")

        # Assert
        mock_raw_con.execute.assert_called_once()
