"""Tests for IntimationRepository archive methods."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from causaganha.storage.repository import IntimationRepository

class MockTable:
    """Mock for Ibis table expression."""
    def __init__(self, data=None):
        self.data = data or []
        self.ia_url = Mock() # Mock column access
        self.link = Mock()

    def filter(self, *args):
        return self

    def limit(self, n):
        return self

    def execute(self):
        mock_res = Mock()
        mock_res.to_dict.return_value = self.data
        return mock_res

@pytest.fixture
def repository():
    """Create repository with mock connection."""
    con = Mock()
    return IntimationRepository(con)

@pytest.mark.asyncio
async def test_get_unarchived_intimations(repository):
    """Test fetching unarchived intimations."""
    mock_data = [{"id": 1, "link": "http://example.com/doc.pdf"}]

    # Mock the table and query chain
    mock_table = MockTable(mock_data)
    repository.con.table.return_value = mock_table

    # Run method
    result = await repository.get_unarchived_intimations(limit=10)

    # Verify
    assert result == mock_data
    repository.con.table.assert_called_with("intimations")

@pytest.mark.asyncio
async def test_mark_as_archived_success(repository):
    """Test marking intimation as archived."""
    intimation_id = "123"
    ia_url = "https://archive.org/details/test"

    # Mock the raw connection execution
    repository.con.con = Mock()

    await repository.mark_as_archived(intimation_id, ia_url)

    # Verify SQL execution
    repository.con.con.execute.assert_called_once()
    args = repository.con.con.execute.call_args[0]
    assert "UPDATE intimations SET ia_url = ?" in args[0]
    assert args[1] == (ia_url, intimation_id)

@pytest.mark.asyncio
async def test_mark_as_archived_validation(repository):
    """Test validation in mark_as_archived."""
    with pytest.raises(ValueError, match="Intimation ID cannot be empty"):
        await repository.mark_as_archived("", "https://valid.url")

    with pytest.raises(ValueError, match="Invalid IA URL"):
        await repository.mark_as_archived("123", "invalid-url")
